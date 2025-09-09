from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError

from django.core.exceptions import ObjectDoesNotExist

from orders.models import Order
from .serializers import OrderCreateSerializer, OrderOutputSerializer
from .permissions import IsCustomerUser


class OrderCreateAPIView(generics.CreateAPIView):
    """
    POST /api/orders/
    """
    serializer_class = OrderCreateSerializer
    permission_classes = [IsAuthenticated, IsCustomerUser]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data, context={"request": request})
        try:
            serializer.is_valid(raise_exception=True)
        except ValidationError as exc:
            # Falls die Validierung sagt "OfferDetail not found." → als 404 zurück
            detail = exc.detail
            if isinstance(detail, dict) and "offer_detail_id" in detail:
                msglist = detail["offer_detail_id"]
                if any("not found" in str(m).lower() for m in (msglist if isinstance(msglist, list) else [msglist])):
                    return Response({"detail": "OfferDetail not found."}, status=status.HTTP_404_NOT_FOUND)
            raise
        order = serializer.save()
        out = OrderOutputSerializer(order)
        return Response(out.data, status=status.HTTP_201_CREATED)


