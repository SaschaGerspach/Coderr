# offers/api/permissions.py
from rest_framework.permissions import BasePermission
from django.contrib.auth import get_user_model
from profiles.models import Profile
from django.db import models


def is_business_profile(profile) -> bool:
    # 1) CharField mit Choices, das 'business' erlaubt
    for f in profile._meta.fields:
        if isinstance(f, models.CharField):
            choices = getattr(f, "choices", None)
            if choices:
                allowed = {c[0] for c in choices}
                if "business" in allowed:
                    return getattr(profile, f.name) == "business"

    # 2) Häufige Feldnamen für textuelle Typen
    for name in ["profile_type", "type", "user_type", "account_type", "role", "kind", "category"]:
        if hasattr(profile, name):
            return getattr(profile, name) == "business"

    # 3) Bool-Varianten
    for name in ["is_business", "business", "is_vendor"]:
        if hasattr(profile, name):
            return bool(getattr(profile, name))

    # 4) Fallback: nicht ermittelbar
    return False


class IsBusinessUser(BasePermission):
    """
    Erlaubt nur authentifizierten Usern mit Business-Profil.
    """
    message = "Authenticated user is not a 'business' profile."

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        try:
            profile = Profile.objects.get(user=user)
        except Profile.DoesNotExist:
            self.message = "Authenticated user has no profile."
            return False

        if not is_business_profile(profile):
            self.message = "Authenticated user is not a 'business' profile."
            return False

        return True
