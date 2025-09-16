"""Orders API permissions.

Contains object- and request-level permission classes used by the orders
endpoints. These permissions enforce who may create, update, or delete orders.
"""

from rest_framework.permissions import BasePermission


class IsCustomerUser(BasePermission):
    """Allows access only to authenticated users with profile.type == 'customer'.

    Intended for POST /api/orders/ to ensure only customers can create orders.
    """

    message = "Only users with type 'customer' can create orders."

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        prof = getattr(user, "profile", None)
        user_type = getattr(prof, "type", "") if prof else ""
        return user_type == "customer"


class IsOrderBusinessUser(BasePermission):
    """Allows PATCH only if the requester is the business user of the order.

    Requirements:
    - user is authenticated
    - user's profile.type == 'business'
    - user is the business_user of the Order instance
    """

    message = "Only the business user of this order may update its status."

    def has_object_permission(self, request, view, obj):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        prof = getattr(user, "profile", None)
        user_type = getattr(prof, "type", "") if prof else ""
        return user_type == "business" and obj.business_user_id == user.id


class IsAdminStaff(BasePermission):
    """Allows DELETE only if the requester is an authenticated staff (admin) user."""

    message = "Only admin staff users may delete orders."

    def has_permission(self, request, view):
        return bool(
            request.user and request.user.is_authenticated and request.user.is_staff
        )
