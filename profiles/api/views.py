from django.http import Http404
from django.shortcuts import get_object_or_404
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied, NotAuthenticated

from ..models import Profile
from .serializers import ProfilePatchSerializer
from .permissions import IsProfileOwner

class ProfilePartialUpdateView(generics.UpdateAPIView):
    """
    PATCH /api/profile/{pk}/
    pk = User-ID, dessen Profil aktualisiert werden soll.
    """
    serializer_class = ProfilePatchSerializer
    permission_classes = [permissions.IsAuthenticated, IsProfileOwner]
    http_method_names = ["patch"]

    def get_object(self):
        user_id = int(self.kwargs.get("pk"))

        # 1) Erst die Auth/Own-Check – verhindert User/Profil-Enumeration
        if not self.request.user.is_authenticated:
            # Das fängt DRF i.d.R. schon vorher ab (IsAuthenticated), aber der Vollständigkeit halber:
            raise NotAuthenticated()
        if self.request.user.id != user_id:
            # Nicht der Owner → sofort 403, ohne DB-Lookup
            raise PermissionDenied("Du darfst nur dein eigenes Profil bearbeiten.")

        # 2) Owner: Profil holen oder "lazy-create"
        try:
            obj = Profile.objects.select_related("user").get(user_id=user_id)
        except Profile.DoesNotExist:
            obj = Profile.objects.create(user=self.request.user)

        # 3) Objekt-Permissions (bleibt, ist jetzt aber nur noch Owner)
        self.check_object_permissions(self.request, obj)
        return obj

    def patch(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(serializer.data, status=status.HTTP_200_OK)
