# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib import admin

from .models import Exclude, Keyword, Repository, Issue, Failure


class RepositoryAdmin(admin.ModelAdmin):
    list_display = ("repository", "commit")


class IssueAdmin(admin.ModelAdmin):
    list_display = ("repository", "commit_hash", "status",
                    "author", "display_issue_url")

    def display_issue_url(self, issue):
        if issue.is_open():
            return '<a href="{}">respond</a>'.format(issue.get_absolute_url())
        else:
            return ""

    display_issue_url.allow_tags = True


admin.site.register(Exclude)
admin.site.register(Keyword)
admin.site.register(Failure)
admin.site.register(Repository, RepositoryAdmin)
admin.site.register(Issue, IssueAdmin)
