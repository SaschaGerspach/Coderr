from rest_framework.permissions import BasePermission


class IsCustomerReviewer(BasePermission):
    """
    Nur authentifizierte User mit Profile.type == 'customer' dürfen Reviews erstellen.
    (401 wenn nicht authentifiziert – das regelt IsAuthenticated in der View,
     403 wenn authentifiziert, aber kein Customer.)
    """
    message = "Only users with a 'customer' profile can create reviews."

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        prof = getattr(user, "profile", None)
        return getattr(prof, "type", "") == "customer"


class IsReviewOwner(BasePermission):
    message = "Only the review owner may modify this review."

    def has_object_permission(self, request, view, obj):
        user = request.user
        return bool(user and user.is_authenticated and obj.reviewer_id == user.id)