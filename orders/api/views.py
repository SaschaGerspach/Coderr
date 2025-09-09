from django.db.models import Q
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError

from orders.models import Order
from .serializers import OrderCreateSerializer, OrderOutputSerializer, OrderStatusPatchSerializer
from .permissions import IsCustomerUser, IsOrderBusinessUser


class OrderListCreateAPIView(generics.ListCreateAPIView):
    """
    GET  /api/orders/   -> Bestellungen des angemeldeten Users (als customer ODER business)
    POST /api/orders/   -> Bestellung erstellen (nur customer)
    """
    queryset = Order.objects.all()

    def get_permissions(self):
        if self.request.method == "POST":
            return [IsAuthenticated(), IsCustomerUser()]
        return [IsAuthenticated()]

    def get_serializer_class(self):
        # GET: Ausgabe-Serializer (Liste)
        if self.request.method == "GET":
            return OrderOutputSerializer
        # POST: Eingabe-Serializer
        return OrderCreateSerializer

    # --- GET ---
    def get_queryset(self):
        user = self.request.user
        if not user or not user.is_authenticated:
            return Order.objects.none()
        # Nur Orders zurückgeben, an denen der User beteiligt ist (als customer ODER business)
        return (
            super()
            .get_queryset()
            .filter(Q(customer_user=user) | Q(business_user=user))
            .select_related("customer_user", "business_user")
            .order_by("-created_at", "-id")
        )

    # --- POST ---
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data, context={"request": request})
        try:
            serializer.is_valid(raise_exception=True)
        except ValidationError as exc:
            # Optional: Mapping auf 404 für „OfferDetail not found.”,
            # falls du das schon in der POST-Variante haben wolltest.
            detail = exc.detail
            if isinstance(detail, dict) and "offer_detail_id" in detail:
                msglist = detail["offer_detail_id"]
                msgs = msglist if isinstance(msglist, list) else [msglist]
                if any("not found" in str(m).lower() for m in msgs):
                    return Response({"detail": "OfferDetail not found."}, status=status.HTTP_404_NOT_FOUND)
            raise

    #     order = serializer.save()
        order = serializer.save()
        out = OrderOutputSerializer(order)
        return Response(out.data, status=status.HTTP_201_CREATED)

class OrderStatusUpdateAPIView(generics.UpdateAPIView):
    """
    PATCH /api/orders/{id}/
    - nur Status änderbar
    - nur business_user dieser Order & Profil-Typ 'business'
    """
    queryset = Order.objects.all().select_related("customer_user", "business_user")
    serializer_class = OrderStatusPatchSerializer
    permission_classes = [IsAuthenticated, IsOrderBusinessUser]

    def partial_update(self, request, *args, **kwargs):
        # Nur 'status' ist erlaubt → zusätzliche Felder ergeben 400
        allowed = {"status"}
        extra_keys = set(request.data.keys()) - allowed
        if extra_keys:
            return Response(
                {"detail": f"Only 'status' may be updated. Invalid fields: {', '.join(sorted(extra_keys))}."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        # Vollständige Order-Repräsentation zurückgeben (Spec)
        full = OrderOutputSerializer(instance)
        return Response(full.data, status=status.HTTP_200_OK)

    # Für DRF ruft PATCH -> partial_update; wir erzwingen partial=True auch für PUT-Schutz
    def update(self, request, *args, **kwargs):
        kwargs["partial"] = True
        return self.partial_update(request, *args, **kwargs)