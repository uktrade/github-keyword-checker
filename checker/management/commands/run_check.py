from django.core.management.base import BaseCommand, CommandError

from checker.checker import run_check

import logging


class Command(BaseCommand):
    def handle(self, *args, **options):
        logger = logging.getLogger(__name__)
        run_check(logger)
