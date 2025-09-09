from rest_framework.permissions import BasePermission


class IsCustomerUser(BasePermission):
    message = "Only users with type 'customer' can create orders."

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        # Erwartetes Profilfeld: profiles.Profile.type (customer/business)
        prof = getattr(user, "profile", None)
        user_type = getattr(prof, "type", "") if prof else ""
        return user_type == "customer"
