"""Offers API permissions.

Contains request- and object-level permissions used by offer endpoints.
"""

from django.db import models
from django.contrib.auth import get_user_model  # noqa: F401  (kept in case of future use)
from rest_framework.permissions import BasePermission
from profiles.models import Profile


def is_business_profile(profile) -> bool:
    """Return True if the given profile represents a business user.

    Heuristics:
    1) Check CharField choices for a value 'business'.
    2) Check common textual type field names (e.g., 'type', 'profile_type').
    3) Check boolean-style flags (e.g., 'is_business').
    4) Fallback to False if none apply.

    This is intentionally defensive to support slightly different profile schemas.
    """
    # 1) CharField with choices that include 'business'
    for field in profile._meta.fields:
        if isinstance(field, models.CharField):
            choices = getattr(field, "choices", None)
            if choices:
                allowed = {c[0] for c in choices}
                if "business" in allowed:
                    return getattr(profile, field.name) == "business"

    # 2) Common textual type field names
    for name in ["profile_type", "type", "user_type", "account_type", "role", "kind", "category"]:
        if hasattr(profile, name):
            return getattr(profile, name) == "business"

    # 3) Boolean-style flags
    for name in ["is_business", "business", "is_vendor"]:
        if hasattr(profile, name):
            return bool(getattr(profile, name))

    # 4) Fallback
    return False


class IsBusinessUser(BasePermission):
    """Allow access only to authenticated users with a business profile."""

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


class IsOfferOwner(BasePermission):
    """Allow modifications only for the owner of the offer.

    Note: Read permissions (e.g., GET on detail) are handled separately by the view.
    """

    message = "Only the offer owner can modify this offer."

    def has_object_permission(self, request, view, obj):
        # obj is an Offer instance
        return request.user.is_authenticated and obj.owner_id == request.user.id
