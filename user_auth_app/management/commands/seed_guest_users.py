from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from rest_framework.authtoken.models import Token

from profiles.models import Profile

GUESTS = {
    "customer": {"username": "andrey", "password": "asdasd", "email": "andrey@example.com"},
    "business": {"username": "kevin",  "password": "asdasd24", "email": "kevin@example.com"},
}

class Command(BaseCommand):
    help = "Create or update demo guest users for the frontend modal."

    def handle(self, *args, **options):
        User = get_user_model()

        for role, cfg in GUESTS.items():
            u, created = User.objects.get_or_create(
                username=cfg["username"],
                defaults={"email": cfg["email"]},
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f"Created user '{u.username}'"))
            else:
                self.stdout.write(f"User '{u.username}' already exists")

            # set (or reset) password to match the frontend
            u.set_password(cfg["password"])
            u.save(update_fields=["password"])

            # ensure profile with correct type
            prof, _ = Profile.objects.get_or_create(user=u, defaults={"type": role})
            if prof.type != role:
                prof.type = role
                prof.save(update_fields=["type"])

            # ensure token (your /api/login/ returns token, but nice for debugging)
            token, _ = Token.objects.get_or_create(user=u)
            self.stdout.write(f"  → type={role}, token={token.key}")

        self.stdout.write(self.style.SUCCESS("Guest users ready."))
