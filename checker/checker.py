import re
import datetime as dt
from dateutil.parser import parse as parse_date
import sys
import time

from django.conf import settings

from github import Github
from .models import Exclude, Repository, Keyword, Issue


KEYWORD_SEARCH_REGEX = "[^\w]{{1}}{keyword}[^\w]{{1}}"


def get_respositories(client):
    """
    Return a list of all public repos not including excluded repos
    """

    org = client.get_organization("uktrade")

    exclude_list = [er.repository for er in Exclude.objects.all()]

    for repo in org.get_repos():
        if not repo.private and repo.name not in exclude_list:
            yield repo


def get_commits(repository, since, until):

    kwargs = dict(until=until)

    if since:
        kwargs["since"] = since

    for commit in repository.get_commits(**kwargs):
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

    for repo in get_respositories(gh):
        current_time = dt.datetime.now()
        last_checked = Repository.objects.get_last_check_time(repo.name)

        logger.info("Checking {}".format(repo.name))

        commit_time = None

        try:
            for commit in get_commits(repo, last_checked, current_time):

                commit_time = parse_date(commit.raw_data["commit"]["committer"]["date"]).replace(tzinfo=None)

                logger.info("Checking commit: {}".format(commit.sha))

                matches = scan_files(commit, keywords)

                if matches:
                    logger.info("Found: {}".format(matches))
                    Issue.objects.create_from_commit(commit, repo.name, matches)

                time.sleep(settings.GITHUB_QUERY_SLEEP_TIME)

            Repository.objects.set_last_check_time(repo.name, current_time)
        except KeyboardInterrupt:
            sys.exit()
        except:
            if commit_time:
                Repository.objects.set_last_check_time(repo.name, commit_time)
            logger.exception("An error has occurred")
