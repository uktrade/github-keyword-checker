# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from  django.views.generic.base import TemplateView
from django.shortcuts import get_object_or_404
from django.contrib import messages

from .models import Issue


class AuthorResponseView(TemplateView):
    template_name = "user_response.html"

    def post(self, request, *args, **kwargs):

        context = self.get_context_data(**kwargs)

        context["issue"].mark_resolved(
            action_taken="remedial_action_taken" in request.POST,
            comment=request.POST["comment"])

        messages.info(self.request, "Thanks for providing feedback!")

        return self.render_to_response(context)

    def get_context_data(self, **kwargs):
        context = super(AuthorResponseView, self).get_context_data(**kwargs)

        context["issue"] = get_object_or_404(
            Issue, pk=self.kwargs["id"],
            uuid=self.kwargs["uuid"])

        return context
