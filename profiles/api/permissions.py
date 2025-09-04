from rest_framework.permissions import BasePermission, SAFE_METHODS

class IsProfileOwner(BasePermission):
    """
    Schreibzugriff nur für den Besitzer des Profils.
    Erwartung: obj ist ein Profile-Objekt mit .user
    """
    message = "Du darfst nur dein eigenes Profil bearbeiten."

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True
        return request.user.is_authenticated and obj.user_id == request.user.id
    


