"""Profiles API views.

Provides endpoints to retrieve a single profile (by user id) and to update the
owner's own profile. Also exposes list endpoints for business and customer
profiles. Authentication is required for all endpoints; write access is limited
to the profile owner.
"""

from django.shortcuts import get_object_or_404
from rest_framework import generics, permissions, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied
from rest_framework.parsers import JSONParser, FormParser, MultiPartParser


from ..models import Profile
from .serializers import (
    ProfileDetailSerializer,
    ProfilePatchSerializer,
    BusinessProfileListSerializer,
    CustomerProfileListSerializer,
)
from .permissions import IsProfileOwner


class ProfileView(generics.RetrieveUpdateAPIView):
    """
    API endpoint for retrieving or partially updating a single profile.

    - GET `/api/profile/{pk}/` returns the profile for the given user id (`pk`).
    - PATCH `/api/profile/{pk}/` updates only the fields provided and is restricted
      to the owner of the profile (the authenticated user with id `pk`).

    Notes:
    - On PATCH, if the profile does not exist for the owner yet, a new profile is
      lazily created for that user.
    - The owner is inferred from the authenticated request and never taken from
      the payload.
    """

    queryset = Profile.objects.select_related("user")
    serializer_class = ProfileDetailSerializer
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = (JSONParser, FormParser, MultiPartParser)  

    def get_permissions(self):
        """Require ownership for PATCH; otherwise authentication only."""
        if self.request.method == "PATCH":
            return [IsAuthenticated(), IsProfileOwner()]
        return [IsAuthenticated()]

    def get_serializer_class(self):
        """Use the patch serializer for PATCH; the detail serializer otherwise."""
        if self.request.method == "PATCH":
            return ProfilePatchSerializer
        return ProfileDetailSerializer

    def get_object(self):
        """
        Return the profile by user id.

        - For PATCH: ensure the authenticated user matches the path `pk`.
          If the profile does not exist for the owner, lazily create it before
          applying object-level permission checks.
        - For GET: fetch the profile by user id or return 404 if it does not exist.
        """
        user_id = int(self.kwargs["pk"])

        if self.request.method == "PATCH":
            if self.request.user.id != user_id:
                raise PermissionDenied(
                    "You are only allowed to update your own profile."
                )
            try:
                obj = self.queryset.get(user_id=user_id)
            except Profile.DoesNotExist:
                obj = Profile.objects.create(user=self.request.user)
            self.check_object_permissions(self.request, obj)
            return obj

        return get_object_or_404(self.queryset, user_id=user_id)


class BusinessProfileListView(generics.ListAPIView):
    """
    API endpoint for listing all business profiles.

    - GET `/api/profiles/business/` returns profiles with `type="business"`.
    - Authentication is required.
    - The result set is intentionally reduced to the fields specified by the
      `BusinessProfileListSerializer`.
    """

    serializer_class = BusinessProfileListSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Return business profiles only (prefetching user for efficiency)."""
        return Profile.objects.select_related("user").filter(type="business")


class CustomerProfileListView(generics.ListAPIView):
    """
    API endpoint for listing all customer profiles.

    - GET `/api/profiles/customers/` returns profiles with `type="customer"`.
    - Authentication is required.
    - The result set is intentionally reduced to the fields specified by the
      `CustomerProfileListSerializer` (e.g., `uploaded_at` instead of `created_at`).
    """

    serializer_class = CustomerProfileListSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Return customer profiles only (prefetching user for efficiency)."""
        return Profile.objects.select_related("user").filter(type="customer")
