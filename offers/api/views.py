from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from ..models import Offer
from .serializers import OfferSerializer
from .permissions import IsBusinessUser


class OfferCreateAPIView(generics.CreateAPIView):
    queryset = Offer.objects.all()
    serializer_class = OfferSerializer
    permission_classes = [IsAuthenticated, IsBusinessUser]

    def create(self, request, *args, **kwargs):
        """
        Überschrieben, um 201 + Response exakt wie Spec zu liefern.
        """
        return super().create(request, *args, **kwargs)
