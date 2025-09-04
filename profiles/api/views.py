from django.shortcuts import get_object_or_404
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied
from ..models import Profile
from .serializers import ProfileDetailSerializer, ProfilePatchSerializer
from .permissions import IsProfileOwner

class ProfileView(generics.RetrieveUpdateAPIView):
    """
    GET  /api/profile/{pk}/   -> Profil lesen (auth erforderlich)
    PATCH /api/profile/{pk}/  -> eigenes Profil aktualisieren (Owner-only, auto-create)
    pk = User-ID
    """
    queryset = Profile.objects.select_related("user")

    # Standard: GET
    serializer_class = ProfileDetailSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_permissions(self):
        if self.request.method == "PATCH":
            return [permissions.IsAuthenticated(), IsProfileOwner()]
        return [permissions.IsAuthenticated()]

    def get_serializer_class(self):
        if self.request.method == "PATCH":
            return ProfilePatchSerializer
        return ProfileDetailSerializer

    def get_object(self):
        user_id = int(self.kwargs["pk"])

        if self.request.method == "PATCH":
            # Nicht-Owner sofort blocken (kein Leak, ob es das Profil gibt)
            if self.request.user.id != user_id:
                raise PermissionDenied("Du darfst nur dein eigenes Profil bearbeiten.")
            try:
                obj = self.queryset.get(user_id=user_id)
            except Profile.DoesNotExist:
                obj = Profile.objects.create(user=self.request.user)  # lazy-create nur für Owner
            self.check_object_permissions(self.request, obj)
            return obj

        # GET: lesen, 404 wenn nicht vorhanden
        return get_object_or_404(self.queryset, user_id=user_id)


class BusinessProfileListView(generics.ListAPIView):
    """
    GET /api/profiles/business/
    Gibt eine Liste aller Business-Profile zurück (nur authentifizierte Nutzer).
    """
    serializer_class = ProfileDetailSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Profile.objects.select_related("user").filter(type="business")