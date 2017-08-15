
from django.conf.urls import url
from django.contrib import admin

from checker.views import AuthorResponseView
from django.views.generic.base import TemplateView


urlpatterns = [
    url('^issue/(?P<id>\d+)/(?P<uuid>[\w\d-]+)/$', AuthorResponseView.as_view(), name="issue_review"),
    url('^done/$', TemplateView.as_view(template_name="thanks.html"), name="done"),
    url(r'^', admin.site.urls)
]
