"""Reviews API permissions.

Contains request- and object-level permissions for review endpoints.
"""

from rest_framework.permissions import BasePermission


class IsCustomerReviewer(BasePermission):
    """Allow creating reviews only for authenticated users with profile.type == 'customer'.

    Note:
        - 401 (unauthorized) is handled by IsAuthenticated at the view level.
        - This permission returns 403 if the user is authenticated but not a customer.
    """

    message = "Only users with a 'customer' profile can create reviews."

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        profile = getattr(user, "profile", None)
        return getattr(profile, "type", "") == "customer"


class IsReviewOwner(BasePermission):
    """Allow modifications or deletion only by the review owner (reviewer)."""

    message = "Only the review owner may modify this review."

    def has_object_permission(self, request, view, obj):
        user = request.user
        return bool(user and user.is_authenticated and obj.reviewer_id == user.id)
