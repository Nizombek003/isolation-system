import os
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

class Command(BaseCommand):
    def handle(self, *args, **kwargs):
        username = os.getenv("DJANGO_SUPERUSER_USERNAME")
        password = os.getenv("DJANGO_SUPERUSER_PASSWORD")
        email = os.getenv("DJANGO_SUPERUSER_EMAIL", "")

        if not username or not password:
            print("Missing env vars")
            return

        User = get_user_model()

        if not User.objects.filter(username=username).exists():
            User.objects.create_superuser(username, email, password)
            print("Superuser created")
        else:
            print("User already exists")