"""Offers API views.

List and create offers on the same endpoint with pagination, searching, and
filtering. Retrieve, patch, and delete are provided on the offer detail route.
Additionally, provide a dedicated endpoint to retrieve a single OfferDetail.
"""

from decimal import Decimal, InvalidOperation

from django.db.models import Min, Q
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.exceptions import ValidationError
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response

from offers.models import Offer, OfferDetail
from .serializers import (
    OfferSerializer,
    OfferListSerializer,
    OfferDetailViewSerializer,
    OfferPatchSerializer,
    OfferDetailFullSerializer,
)
from .permissions import IsBusinessUser, IsOfferOwner


class OffersPagination(PageNumberPagination):
    """Default pagination for offers with an adjustable page size via query param."""

    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 100


class OfferListCreateAPIView(generics.ListCreateAPIView):
    """GET: paginated list with filters; POST: create offer (business-only)."""

    queryset = Offer.objects.all().select_related("owner").prefetch_related("details")
    pagination_class = OffersPagination

    def get_permissions(self):
        """Allow only business users to create offers; list is public."""
        if self.request.method == "POST":
            return [IsAuthenticated(), IsBusinessUser()]
        return [AllowAny()]

    def get_serializer_class(self):
        """Use list serializer for GET and creation serializer for POST."""
        if self.request.method == "GET":
            return OfferListSerializer
        return OfferSerializer

    def get_queryset(self):
        qs = self._annotate_base(super().get_queryset())
        qs = self._apply_filters(qs, self.request.query_params)
        return self._apply_ordering(qs, self.request.query_params.get("ordering"))

    # --- helpers ---
    def _annotate_base(self, qs):
        return qs.annotate(
            _min_price=Min("details__price"),
            _min_delivery=Min("details__delivery_time_in_days"),
        )

    def _apply_filters(self, qs, params):
        creator_id = params.get("creator_id")
        if creator_id is not None:
            if not creator_id.isdigit():
                raise ValidationError({"creator_id": "Must be an integer."})
            qs = qs.filter(owner_id=int(creator_id))

        min_price = params.get("min_price")
        if min_price is not None:
            try:
                mp = Decimal(min_price)
            except (InvalidOperation, TypeError):
                raise ValidationError({"min_price": "Must be a number."})
            qs = qs.filter(_min_price__gte=mp)

        max_delivery = params.get("max_delivery_time")
        if max_delivery is not None:
            if not max_delivery.isdigit():
                raise ValidationError({"max_delivery_time": "Must be an integer."})
            qs = qs.filter(_min_delivery__lte=int(max_delivery))

        search = params.get("search")
        if search:
            qs = qs.filter(Q(title__icontains=search) | Q(description__icontains=search))

        return qs

    def _apply_ordering(self, qs, ordering):
        if not ordering:
            return qs.order_by("-updated_at", "id")

        allowed = {"updated_at", "-updated_at", "min_price", "-min_price"}
        if ordering not in allowed:
            raise ValidationError(
                {"ordering": "Allowed values: updated_at, -updated_at, min_price, -min_price."}
            )

        if "min_price" in ordering:
            ordering = ordering.replace("min_price", "_min_price")
        return qs.order_by(ordering)


class OfferRetrieveUpdateDestroyAPIView(generics.RetrieveUpdateDestroyAPIView):
    """GET: retrieve offer, PATCH/PUT: update (owner only), DELETE: remove (owner only)."""

    queryset = Offer.objects.all().select_related("owner").prefetch_related("details")

    def get_permissions(self):
        """Enforce offer ownership for modifications; auth required for read."""
        if self.request.method in ["PATCH", "PUT", "DELETE"]:
            return [IsAuthenticated(), IsOfferOwner()]
        return [IsAuthenticated()]

    def get_queryset(self):
        """Annotate min price and delivery time for the detail serializer."""
        return super().get_queryset().annotate(
            _min_price=Min("details__price"),
            _min_delivery=Min("details__delivery_time_in_days"),
        )

    def get_serializer_class(self):
        """Use the appropriate serializer for GET vs. PATCH/PUT."""
        if self.request.method == "GET":
            return OfferDetailViewSerializer
        if self.request.method in ["PATCH", "PUT"]:
            return OfferPatchSerializer
        return OfferDetailViewSerializer

    def update(self, request, *args, **kwargs):
        """Perform a partial update and return the full offer payload."""
        partial = kwargs.pop("partial", True)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        full = OfferSerializer(instance, context={"request": request})
        return Response(full.data, status=status.HTTP_200_OK)

    def destroy(self, request, *args, **kwargs):
        """Delete the offer and respond with 204 No Content."""
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)


class OfferDetailRetrieveAPIView(generics.RetrieveAPIView):
    """GET /api/offerdetails/{id}/ -> return a single OfferDetail."""

    queryset = OfferDetail.objects.all()
    serializer_class = OfferDetailFullSerializer
    permission_classes = [IsAuthenticated]
