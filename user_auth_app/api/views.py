"""Auth API views.

Implements token-based registration and login. Registration will also create a
Profile with the provided `type` if it does not exist.
"""

from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.response import Response
from rest_framework.views import APIView

from profiles.models import Profile
from .permissions import AllowAnyRegistration, AllowedAnyLogin
from .serializers import LoginSerializer, RegistrationSerializer

User = get_user_model()


class RegistrationView(APIView):
    """POST /api/registration/ -> create user, profile (type), return auth token."""

    permission_classes = [AllowAnyRegistration]

    def post(self, request, *args, **kwargs):
        serializer = RegistrationSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        user = serializer.save()
        profile_type = serializer.validated_data.get("type", "")
        # Create the profile with the requested type if absent.
        Profile.objects.get_or_create(user=user, defaults={"type": profile_type})

        token, _ = Token.objects.get_or_create(user=user)
        data = {
            "token": token.key,
            "username": user.username,
            "email": user.email,
            "user_id": user.id,
        }
        return Response(data, status=status.HTTP_201_CREATED)


class LoginView(APIView):
    """POST /api/login/ -> validate credentials and return auth token."""

    permission_classes = [AllowedAnyLogin]

    def post(self, request, *args, **kwargs):
        serializer = LoginSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        user = serializer.validated_data["user"]
        token, _ = Token.objects.get_or_create(user=user)
        data = {
            "token": token.key,
            "username": user.username,
            "email": user.email,
            "user_id": user.id,
        }
        return Response(data, status=status.HTTP_200_OK)
