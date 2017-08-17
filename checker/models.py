# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import os
import uuid

from django.db import models
from django.urls import reverse
from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string


class Exclude(models.Model):
    """
    Excluded repositories
    """

    repository = models.CharField(max_length=255)

    def __unicode__(self):
        return self.repository


class Keyword(models.Model):
    """
    Keywords to scan for
    """

    text = models.CharField(max_length=255)

    def save(self, *args, **kwargs):
        self.text = self.text.lower()

        super(Keyword, self).save(*args, **kwargs)

    def __unicode__(self):
        return self.text


class Failure(models.Model):
    commit = models.CharField(max_length=255)
    repository = models.CharField(max_length=255)
    branch = models.CharField(max_length=255)

    def __unicode__(self):
        return "{} / {} / {}".format(self.repository, self.branch, self.commit)


class Repository(models.Model):

    checked = models.DateTimeField(auto_now_add=True, blank=True, null=True)
    commit = models.CharField(blank=True, null=True, max_length=255)

    repository = models.CharField(max_length=255)

    def __unicode__(self):
        return "{} - {}".format(self.repository, self.hash)

    class Meta:
        verbose_name_plural = "Repositories"


class IssueManager(models.Manager):
    def create_from_commit(self, commit, repository, matches, org_users):

        matches_text = "\n".join(
            ["File: {} contains keywords: {}".format(
                item[0],
                ", ".join(item[1])) for item in matches]
        )

        if commit.author:
            # commit.autohr filed is not always set
            login = commit.author.login
            email = commit.author.email
        else:
            login, email = "", ""

        email = os.environ.get(
            "OVERRIDE_EMAIL_ADDRESS", email)

        if not email:
            status = Issue.STATUS_NO_EMAIL
        elif login and login not in org_users:
            status = Issue.STATUS_USER_NOT_IN_ORG
        else:
            status = Issue.STATUS_AWAITING_RESPONSE

        issue = self.create(
            status=status,
            repository=repository,
            commit_hash=commit.sha,
            author=login,
            url=commit.html_url,
            author_email=email,
            report=matches_text
        )

        if settings.NOTIFY_USER:
            issue.notify_author()

        return issue


class Issue(models.Model):

    STATUS_NO_EMAIL = 0
    STATUS_AWAITING_RESPONSE = 1
    STATUS_USER_NOT_IN_ORG = 2
    STATUS_RESOLVED_NO_ACTION_TAKEN = 3
    STATUS_RESOLVED_ACTION_TAKEN = 4

    ACTION_CHOICES = (
        (STATUS_NO_EMAIL, "Email address not available - unable to notify"),
        (STATUS_AWAITING_RESPONSE, "Awaiting response"),
        (STATUS_RESOLVED_NO_ACTION_TAKEN, "Resolved: No action required"),
        (STATUS_RESOLVED_ACTION_TAKEN, "Resolved: Action taken"),
        (STATUS_USER_NOT_IN_ORG, "Author no longer works for organisation")
    )

    STATUS_REQUIRES_ACTION = [STATUS_NO_EMAIL, STATUS_AWAITING_RESPONSE, STATUS_USER_NOT_IN_ORG]

    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    repository = models.CharField(max_length=255)
    status = models.PositiveIntegerField(choices=ACTION_CHOICES)
    commit_hash = models.CharField(max_length=255)

    author = models.CharField(max_length=255)
    author_email = models.EmailField(max_length=255, blank=True, null=True)
    author_response = models.TextField()

    url = models.URLField(null=True, blank=True)

    report = models.TextField(blank=True)

    objects = IssueManager()

    def __unicode__(self):
        return "{} / {} / {}".format(
            self.repository, self.author, self.get_status_display())

    def get_absolute_url(self):
        return reverse("issue_review", kwargs=dict(id=self.id, uuid=str(self.uuid)))

    def is_open(self):
        return self.status in Issue.STATUS_REQUIRES_ACTION

    def notify_author(self):

        if self.author_email:
            context = dict(
                issue=self,
                host=settings.HOST)

            message = render_to_string("email.txt", context=context)
            send_mail(
                settings.NOTIFY_EMAIL_SUBJECT, message,
                settings.NOTIFY_EMAIL_FROM, [self.author_email])

    def mark_resolved(self, action_taken, comment):

        if action_taken:
            status = Issue.STATUS_RESOLVED_NO_ACTION_TAKEN
        else:
            status = Issue.STATUS_RESOLVED_NO_ACTION_TAKEN

        self.status = status
        self.author_response = comment
        self.save()

        if settings.NOTIFY_USER:
            self.notify_author()
