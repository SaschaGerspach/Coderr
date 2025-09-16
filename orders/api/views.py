"""Orders API views.

List and create orders on the same endpoint, return only orders that involve
the authenticated user (as customer or business). Provide detail update/delete
with object-level permission checks. Also provide count endpoints for
in-progress and completed orders for a given business user.
"""

from django.db.models import Q
from django.contrib.auth import get_user_model
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from rest_framework.views import APIView

from orders.models import Order
from .serializers import (
    OrderCreateSerializer,
    OrderOutputSerializer,
    OrderStatusPatchSerializer,
)
from .permissions import IsCustomerUser, IsOrderBusinessUser, IsAdminStaff

User = get_user_model()


# ----------------------------- helpers (module-level) -----------------------------

def _user_orders_queryset(base_qs, user):
    """Orders, an denen der User beteiligt ist (customer ODER business)."""
    if not user or not user.is_authenticated:
        return Order.objects.none()
    return (
        base_qs.filter(Q(customer_user=user) | Q(business_user=user))
        .select_related("customer_user", "business_user")
        .order_by("-created_at", "-id")
    )


def _map_offerdetail_not_found(exc: ValidationError):
    """
    Mappt das bekannte Validierungsformat auf 404, wenn offer_detail_id „not found“ meldet.
    Gibt Response | None zurück.
    """
    detail = exc.detail
    if isinstance(detail, dict) and "offer_detail_id" in detail:
        msgs = detail["offer_detail_id"]
        if not isinstance(msgs, (list, tuple)):
            msgs = [msgs]
        if any("not found" in str(m).lower() for m in msgs):
            return Response({"detail": "OfferDetail not found."}, status=status.HTTP_404_NOT_FOUND)
    return None


def _validate_patch_only_status(data: dict):
    """Erlaube nur 'status' im PATCH; liefere evtl. 400-Response zurück."""
    allowed = {"status"}
    extra = set(data.keys()) - allowed
    if extra:
        return Response(
            {"detail": f"Only 'status' may be updated. Invalid fields: {', '.join(sorted(extra))}."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    return None


def _business_user_or_404(business_user_id: int):
    """Hole Business-User inkl. Profil oder liefere (None, Response(404)) zurück."""
    try:
        user = User.objects.select_related("profile").get(id=business_user_id)
    except User.DoesNotExist:
        return None, Response({"detail": "Business user not found."}, status=status.HTTP_404_NOT_FOUND)
    prof = getattr(user, "profile", None)
    if not prof or getattr(prof, "type", "") != "business":
        return None, Response({"detail": "Business user not found."}, status=status.HTTP_404_NOT_FOUND)
    return user, None


def _count_orders(business_user_id: int, status_value: str, key: str):
    """Zähle Orders für business_user_id mit gegebenem Status und liefere JSON."""
    count = Order.objects.filter(business_user_id=business_user_id, status=status_value).count()
    return Response({key: count}, status=status.HTTP_200_OK)


# --------------------------------------- views ---------------------------------------

class OrderListCreateAPIView(generics.ListCreateAPIView):
    """GET: list orders of the authenticated user (as customer or business).
    POST: create a new order from an OfferDetail (customer-only).
    """

    queryset = Order.objects.all()

    def get_permissions(self):
        """Customer-only on POST, otherwise just authenticated."""
        if self.request.method == "POST":
            return [IsAuthenticated(), IsCustomerUser()]
        return [IsAuthenticated()]

    def get_serializer_class(self):
        """Use output serializer for GET and input serializer for POST."""
        return OrderOutputSerializer if self.request.method == "GET" else OrderCreateSerializer

    # --- GET ---
    def get_queryset(self):
        """Return only orders where the authenticated user is involved."""
        return _user_orders_queryset(super().get_queryset(), self.request.user)

    # --- POST ---
    def create(self, request, *args, **kwargs):
        """Validate and create a new order, returning the full order payload."""
        serializer = self.get_serializer(data=request.data, context={"request": request})
        try:
            serializer.is_valid(raise_exception=True)
        except ValidationError as exc:
            mapped = _map_offerdetail_not_found(exc)
            if mapped is not None:
                return mapped
            raise
        order = serializer.save()
        return Response(OrderOutputSerializer(order).data, status=status.HTTP_201_CREATED)


class OrderDetailUpdateDeleteAPIView(generics.RetrieveUpdateDestroyAPIView):
    """PATCH: update status (business user of the order only).
    DELETE: delete order (staff only).
    """

    queryset = Order.objects.all().select_related("customer_user", "business_user")

    def get_permissions(self):
        """Apply method-specific permissions for PATCH and DELETE."""
        if self.request.method == "PATCH":
            return [IsAuthenticated(), IsOrderBusinessUser()]
        if self.request.method == "DELETE":
            return [IsAuthenticated(), IsAdminStaff()]
        return [IsAuthenticated()]  # fallback if GET is ever enabled

    def get_serializer_class(self):
        """Use status patch serializer for PATCH; output serializer otherwise."""
        return OrderStatusPatchSerializer if self.request.method == "PATCH" else OrderOutputSerializer

    def partial_update(self, request, *args, **kwargs):
        """Allow updating only 'status'; return full order after update."""
        bad = _validate_patch_only_status(request.data)
        if bad is not None:
            return bad
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(OrderOutputSerializer(instance).data, status=status.HTTP_200_OK)


class OrderCountAPIView(APIView):
    """GET /api/order-count/{business_user_id}/ -> {"order_count": <int>}.
    Returns the number of in-progress orders for the given business user.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, business_user_id: int):
        user, err = _business_user_or_404(business_user_id)
        if err:
            return err
        return _count_orders(user.id, Order.Status.IN_PROGRESS, "order_count")


class CompletedOrderCountAPIView(APIView):
    """GET /api/completed-order-count/{business_user_id}/ -> {"completed_order_count": <int>}.
    Returns the number of completed orders for the given business user.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, business_user_id: int):
        user, err = _business_user_or_404(business_user_id)
        if err:
            return err
        return _count_orders(user.id, Order.Status.COMPLETED, "completed_order_count")
