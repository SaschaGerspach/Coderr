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
