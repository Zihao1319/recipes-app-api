""""wait for db to be available"""

from operator import truediv
import time

from psycopg2 import OperationalError as Psycopg20pError

from django.db.utils import OperationalError

from django.core.management.base import BaseCommand

class Command(BaseCommand):
    """django command to wait for db"""

    def handle (self, *args, **options):
        """entry  point for command"""
        self.stdout.write("waiting for db...")
        db_up = False
        while db_up is False:
            try:
                self.check(databases= ["default"])
                db_up=True
            except (Psycopg20pError, OperationalError):
                self.stdout.write("db unavailable, waiting 1s")
                time.sleep(1)
        self.stdout.write(self.style.SUCCESS("db available!"))

