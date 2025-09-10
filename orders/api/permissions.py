from rest_framework.permissions import BasePermission

class IsCustomerUser(BasePermission):
    message = "Only users with type 'customer' can create orders."

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        prof = getattr(user, "profile", None)
        user_type = getattr(prof, "type", "") if prof else ""
        return user_type == "customer"


class IsOrderBusinessUser(BasePermission):
    """
    Erlaubt PATCH nur, wenn:
    - der User authentifiziert ist
    - sein Profile.type == 'business'
    - und er der business_user der Order ist
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
    message = "Only admin staff users may delete orders."

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_staff)
