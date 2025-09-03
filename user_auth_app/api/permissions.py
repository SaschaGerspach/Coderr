from rest_framework.permissions import AllowAny, BasePermission
from rest_framework.request import Request
from rest_framework.views import View


class AllowAnyRegistration(AllowAny):
    """
    Spezifische Permission-Klasse für die Registrierung.
    """
    pass


class AllowedAnyLogin(AllowAny):
    pass


class IsAnonymous(BasePermission):
    """
    Alternative: erlaubt nur anonymen Nutzern den Zugriff.
    """

    def has_permission(self, request: Request, view: View) -> bool:
        return not request.user or not request.user.is_authenticated
