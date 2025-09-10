from django.db.models import Q
from django.contrib.auth import get_user_model
from rest_framework.views import APIView
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError

from orders.models import Order
from .serializers import OrderCreateSerializer, OrderOutputSerializer, OrderStatusPatchSerializer
from .permissions import IsCustomerUser, IsOrderBusinessUser, IsAdminStaff

User = get_user_model()

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

class OrderDetailUpdateDeleteAPIView(generics.RetrieveUpdateDestroyAPIView):
    """
    PATCH /api/orders/<id>/  -> Status aktualisieren (nur business_user dieser Order)
    DELETE /api/orders/<id>/ -> Löschen (nur Staff)
    """
    queryset = Order.objects.all().select_related("customer_user", "business_user")

    def get_permissions(self):
        if self.request.method == "PATCH":
            return [IsAuthenticated(), IsOrderBusinessUser()]
        if self.request.method == "DELETE":
            return [IsAuthenticated(), IsAdminStaff()]
        return [IsAuthenticated()]  # falls GET jemals genutzt wird

    def get_serializer_class(self):
        if self.request.method == "PATCH":
            return OrderStatusPatchSerializer
        return OrderOutputSerializer

    def partial_update(self, request, *args, **kwargs):
        # nur 'status' ist erlaubt
        allowed = {"status"}
        extra = set(request.data.keys()) - allowed
        if extra:
            return Response(
                {"detail": f"Only 'status' may be updated. Invalid fields: {', '.join(sorted(extra))}."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        # volle Order zurückgeben
        return Response(OrderOutputSerializer(instance).data, status=status.HTTP_200_OK)
    

class OrderCountAPIView(APIView):
    """
    GET /api/order-count/{business_user_id}/
    Gibt {"order_count": <int>} zurück.
    Auth erforderlich.
    404, wenn kein Business-User mit der ID existiert.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, business_user_id: int):
        try:
            user = User.objects.select_related("profile").get(id=business_user_id)
        except User.DoesNotExist:
            return Response({"detail": "Business user not found."}, status=status.HTTP_404_NOT_FOUND)

        # Muss ein Business-Profil sein
        prof = getattr(user, "profile", None)
        if not prof or getattr(prof, "type", "") != "business":
            return Response({"detail": "Business user not found."}, status=status.HTTP_404_NOT_FOUND)

        count = Order.objects.filter(
            business_user_id=business_user_id,
            status=Order.Status.IN_PROGRESS,
        ).count()
        return Response({"order_count": count}, status=status.HTTP_200_OK)