# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from unittest.mock import MagicMock, Mock
import datetime as dt

from django.test import TestCase, override_settings
from django.core import mail
from django.conf import settings

from .models import Issue, Repository
from .checker import process_patch


class RepositoryTestCase(TestCase):
    def test_get_last_check_time__new_repo(self):

        self.assertIsNone(Repository.objects.get_last_check_time("test_repo"))

    def test_get_last_check_time__existing_repo(self):

        now = dt.datetime.now()

        Repository.objects.set_last_check_time("test_repo", now)

        self.assertEquals(now, Repository.objects.get_last_check_time("test_repo"))

    def test_set_last_check_time(self):

        now = dt.datetime.now()

        Repository.objects.set_last_check_time("test_repo", now)

        repo = Repository.objects.first()
        self.assertEquals(repo.check_time, now)
        self.assertEquals(repo.repository, "test_repo")


class ModelsTestCase(TestCase):
    def test_issue_notify_author(self):
        issue = Issue(author_email="test@test.com")
        issue.id = 1
        issue.notify_author()

        self.assertEquals(len(mail.outbox), 1)
        self.assertEquals(settings.NOTIFY_EMAIL_SUBJECT, mail.outbox[0].subject)
        self.assertEquals(mail.outbox[0].to, [issue.author_email])

    def get_mock_commit(self):
        author_mock = Mock(login="github-user",
                           email="email")

        return Mock(sha="sha",
                    html_url="html-url",
                    author=author_mock)

    def test_create_from_commit(self):
        Issue.objects.create_from_commit(self.get_mock_commit(), "test_repo",
                                         [["somefile.txt", ["some matches"]]])

        issue = Issue.objects.first()

        self.assertEquals(issue.commit_hash, "sha")
        self.assertEquals(issue.status, 1)
        self.assertEquals(issue.author, "github-user")
        self.assertEquals(issue.url, "html-url")
        self.assertEquals(issue.author_email, "email")


class CheckerTestCase(TestCase):

    def test_process_patch_correctly_removes_lines(self):
        raw_patch = """@@ -19,42 +19,55 @@
 # proxy "/this-page-has-no-template.html", "/template-file.html", locals: {
 #  which_fake_page: "Rendering a fake page with a local variable" }

-data.countries.each do |country|
-  file_url = country.name.downcase.gsub(' ', '-').gsub(/[^a-z0-9-]/,'')
-  country[:data] = country[:data] || {
-    :gdp => "39,189",
-    :population => "63m",
-    :exchange_rate => 0.67,
-    :currency => "Euro",
-    :inflation => 3,
-    :growth => 0.6,
-    :deficit => -4.6,
-    :imports => "639b",
-    :imports_uk => "700m",
-  }
-
-  proxy "/markets/#{file_url}.html", "/market.html", :locals => { :country => country }, :ignore => true
-end
+ready do
+  app.data.countries.each do |country|
+    country[:stub] = country.name.downcase.gsub(' ', '-').gsub(/[^a-z0-9-]/,'')
+    country[:url] = "/markets/#{country[:stub]}/index.html"
+    country[:data] = country[:data] || {
+      gdp: "39,189",
+      population: "63m",
+      exchange_rate: 0.67,
+      currency: "Euro",
+      inflation: 3,
+      growth: 0.6,
+      deficit: -4.6,
+      imports: "639b",
+      imports_uk: "700m",
+      unemployment: 5,
+    }
+
+    app.data.industries.each do |k,industry|
+      industry[:stub] = industry.name.downcase.gsub(' ', '-').gsub(/[^a-z0-9-]/,'')
+      industry[:url] = "markets/#{country[:stub]}/#{industry[:stub]}.html"
+      proxy industry[:url], "/industry.html", :locals => { :industry => industry, :country => country }, :ignore => true
+    end
"""

        result = """@@ -19,42 +19,55 @@
 # proxy "/this-page-has-no-template.html", "/template-file.html", locals: {
 #  which_fake_page: "Rendering a fake page with a local variable" }

+ready do
+  app.data.countries.each do |country|
+    country[:stub] = country.name.downcase.gsub(' ', '-').gsub(/[^a-z0-9-]/,'')
+    country[:url] = "/markets/#{country[:stub]}/index.html"
+    country[:data] = country[:data] || {
+      gdp: "39,189",
+      population: "63m",
+      exchange_rate: 0.67,
+      currency: "Euro",
+      inflation: 3,
+      growth: 0.6,
+      deficit: -4.6,
+      imports: "639b",
+      imports_uk: "700m",
+      unemployment: 5,
+    }
+
+    app.data.industries.each do |k,industry|
+      industry[:stub] = industry.name.downcase.gsub(' ', '-').gsub(/[^a-z0-9-]/,'')
+      industry[:url] = "markets/#{country[:stub]}/#{industry[:stub]}.html"
+      proxy industry[:url], "/industry.html", :locals => { :industry => industry, :country => country }, :ignore => true
+    end
"""
        self.assertEquals(process_patch(raw_patch), result)

    def test_process_patch_raises_exception_if_invalid_format(self):
        with self.assertRaises(Exception):
            process_patch("this is not a patch file")

    def test_keyword_searching(self):

        keyword = "defence"

        valid_matches = [
            "defence*",
            "*defence",
            "*defence*"
        ]

        invalid_matches = [
            "   defences   ",
            "1234defence123",
            "aaadefenceaaa",
            "adefence*",
            "*defencez"
        ]

# TODO: integration tests:
# Test exceptions are logged
# The case of an exception the last updated date isn't set