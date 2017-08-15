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


class RepositoryManager(models.Manager):
    def get_last_check_time(self, repository):
        last = self.filter(repository=repository).order_by("-id").first()

        if last:
            return last.check_time
        else:
            return None

    def set_last_check_time(self, repository, last_checked):
        self.get_or_create(
            repository=repository,
            defaults={"check_time": last_checked})


class Repository(models.Model):

    check_time = models.DateTimeField(
        help_text="The last time the github API was queried for this repo.")

    repository = models.CharField(max_length=255)

    def __unicode__(self):
        return "{} - {}".format(self.repository, self.check_time)

    objects = RepositoryManager()

    class Meta:
        verbose_name_plural = "Repositories"


class IssueManager(models.Manager):
    def create_from_commit(self, commit, repository, matches):

        matches_text = "\n".join(
            ["File: {} contains keywords: {}".format(
                item[0],
                ", ".join(item[1])) for item in matches]
        )

        email = os.environ.get(
            "OVERRIDE_EMAIL_ADDRESS", commit.author.email)

        status = 1 if email else 0

        issue = self.create(
            status=status,
            repository=repository,
            commit_hash=commit.sha,
            author=commit.author.login,
            url=commit.html_url,
            author_email=email,
            report=matches_text
        )

        if settings.NOTIFY_USER:
            issue.notify_author()

        return issue


class Issue(models.Model):

    ACTION_CHOICES = (
        (0, "Email address not available - unable to notify"),
        (1, "Awaiting response"),
        (2, "Resolved: No action required"),
        (3, "Resolved: Action taken"),
    )

    STATUS_REQUIRES_ACTION = [0, 1]

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
        status = 3 if action_taken else 2
        self.status = status
        self.author_response = comment
        self.save()

        if settings.NOTIFY_AUTHOR:
            self.notify_author()
