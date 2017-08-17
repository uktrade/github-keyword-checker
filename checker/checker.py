import re
import sys
from ssl import SSLError
import time

from django.conf import settings

from github import Github
from .models import Exclude, Repository, Keyword, Issue, Failure


KEYWORD_SEARCH_REGEX = "[^\w]{{1}}{keyword}[^\w]{{1}}"


def get_branches(repo):
    """
    return the tuple with the default branch and other branches
    """

    return [repo.default_branch] + [r.name for r in repo.get_branches() if r.name != repo.default_branch]

def get_org_users(client):

    org = client.get_organization(settings.GITHUB_ORGANISATION)

    return [m.login for m in org.get_members()]


def get_respositories(client):
    """
    Return a list of all public repos not including excluded repos
    """

    org = client.get_organization(settings.GITHUB_ORGANISATION)

    exclude_list = [er.repository for er in Exclude.objects.all()]

    for repo in org.get_repos():
        if not repo.private and repo.name not in exclude_list:
            yield repo


def get_commits(repository, branch):

    for commit in repository.get_commits(sha=branch):
        yield commit


def scan_files(commit, keywords):
    matches = []
    for file_ in commit.raw_data["files"]:
        if "patch" not in file_:
            # Assume a lack of a patch field indicates a binary file?
            # It could also mean a new file?  Need to verify this.
            continue

        found_keywords = search_text(file_["patch"], keywords)

        if found_keywords:
            matches.append((
                file_["filename"],
                found_keywords,
            ))

    return matches


def process_patch(patch):
    """
    Rather dirty function to remove any lines that would being removed by the
    patch prior to checking it for keywords.
    """

    if not patch.startswith("@@"):
        raise Exception("This is not a unidiff")

    return "\n".join(line for line in patch.split("\n") if not line.startswith("-"))


def search_text(text, keywords):
    """
    Search text for keywords.
    """
    text = text.lower()
    found = []

    for keyword in keywords:
        # NOTE: python maintains a regex cache, so re.compile is not strictly necessary
        # (unless we're using
        regex = KEYWORD_SEARCH_REGEX.format(keyword=keyword)

        if re.search(regex, text, re.I):
            found.append(keyword)

    return found


def run_check(logger):

    keywords = [k.text for k in Keyword.objects.all()]

    gh = Github(settings.GITHUB_ACCESS_TOKEN)

    org_users = get_org_users(gh)

    for repo in get_respositories(gh):

        for branch in get_branches(repo):

            logger.info("Checking branch {} in {}".format(branch, repo.name))

            for commit in get_commits(repo, branch):
                try:
                    if Repository.objects.filter(
                            repository=repo.name, commit=commit.sha).exists():
                        # we've already scanned this far, assume older
                        # commits have already been scanned
                        break

                    logger.info("Checking {}".format(commit.sha))

                    matches = scan_files(commit, keywords)

                    if matches:
                        logger.info("Found: {}".format(matches))
                        Issue.objects.create_from_commit(
                            commit, repo.name, matches, org_users)

                    Repository.objects.create(
                        commit=commit.sha, repository=repo.name)

                    time.sleep(settings.GITHUB_QUERY_SLEEP_TIME)
                except SSLError:
                    logger.error("Connection error")
                    Failure.objects.create(
                        repository=repo.name, branch=branch, commit=commit.sha)
                except KeyboardInterrupt:
                    sys.exit()
                except:
                    import pdb; pdb.set_trace()
                    logger.exception("An error has occurred")
