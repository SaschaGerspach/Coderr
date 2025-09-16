"""Profiles API permissions.

Contains custom permission classes used by profile endpoints.
"""

from rest_framework.permissions import BasePermission, SAFE_METHODS


class IsProfileOwner(BasePermission):
    """
    Object-level permission that allows write access only to the profile owner.

    - SAFE methods (GET/HEAD/OPTIONS) are always allowed.
    - For write methods (e.g., PATCH), the user must be authenticated and
      match the profile's owner (`obj.user_id == request.user.id`).
    """

    message = "You may only modify your own profile."

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True
        return request.user.is_authenticated and obj.user_id == request.user.id
