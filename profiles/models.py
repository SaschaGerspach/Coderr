"""Profiles app models.

Defines the Profile model that extends the base user with additional metadata
and role information (customer/business). String fields intentionally default to
empty strings to avoid nulls in API responses.
"""

from django.db import models
from django.conf import settings


class Profile(models.Model):
    """
    Profile for a single user.

    Stores general information for both customer and business user types.
    A profile is created at most once per user (OneToOne relationship).
    """

    USER_TYPES = (("customer", "customer"), ("business", "business"))

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile",
    )
    file = models.CharField(max_length=255, blank=True, default="")
    location = models.CharField(max_length=255, blank=True, default="")
    tel = models.CharField(max_length=50, blank=True, default="")
    description = models.TextField(blank=True, default="")
    working_hours = models.CharField(max_length=50, blank=True, default="")
    type = models.CharField(
        max_length=20,
        choices=USER_TYPES,
        blank=True,
        default="",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        """Readable representation for admin and debugging."""
        return f"Profile<{self.user_id}:{self.user.username}>"
