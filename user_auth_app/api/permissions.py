"""Auth API permissions.

Lightweight permissions used by registration/login endpoints and an optional
anonymous-only gate.
"""

from rest_framework.permissions import AllowAny, BasePermission
from rest_framework.request import Request
from rest_framework.views import View


class AllowAnyRegistration(AllowAny):
    """Explicit alias for registration endpoints (semantics: allow any)."""
    pass


class AllowedAnyLogin(AllowAny):
    """Explicit alias for login endpoints (semantics: allow any)."""
    pass


class IsAnonymous(BasePermission):
    """Grant access only to anonymous (unauthenticated) users."""

    def has_permission(self, request: Request, view: View) -> bool:
        return not request.user or not request.user.is_authenticated
