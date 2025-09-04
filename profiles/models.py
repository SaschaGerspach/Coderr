from django.db import models
from django.conf import settings

class Profile(models.Model):
    USER_TYPES = (("customer", "customer"), ("business", "business"))

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile",
    )
    # einfache Felder (Strings, im Zweifel leer statt null)
    file = models.CharField(max_length=255, blank=True, default="")
    location = models.CharField(max_length=255, blank=True, default="")
    tel = models.CharField(max_length=50, blank=True, default="")
    description = models.TextField(blank=True, default="")
    working_hours = models.CharField(max_length=50, blank=True, default="")
    type = models.CharField(max_length=20, choices=USER_TYPES, blank=True, default="")

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Profile<{self.user_id}:{self.user.username}>"
