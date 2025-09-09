from decimal import Decimal, InvalidOperation

from django.db.models import Min, Q
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.exceptions import ValidationError
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response


from offers.models import Offer, OfferDetail
from .serializers import OfferSerializer, OfferListSerializer, OfferDetailViewSerializer, OfferPatchSerializer, OfferDetailFullSerializer
from .permissions import IsBusinessUser, IsOfferOwner



class OffersPagination(PageNumberPagination):
    page_size = 10  # Default
    page_size_query_param = "page_size"
    max_page_size = 100  # Safety-Cap


class OfferListCreateAPIView(generics.ListCreateAPIView):
    """
    GET /api/offers/  -> paginierte Liste
    POST /api/offers/ -> wie zuvor (nur Business, Owner aus request.user)
    """
    queryset = Offer.objects.all().select_related("owner").prefetch_related("details")
    pagination_class = OffersPagination

    def get_permissions(self):
        if self.request.method == "POST":
            return [IsAuthenticated(), IsBusinessUser()]
        return [AllowAny()]

    def get_serializer_class(self):
        if self.request.method == "GET":
            return OfferListSerializer
        return OfferSerializer

    def get_queryset(self):
        qs = super().get_queryset()

        # Annotationen für min_price / min_delivery_time
        qs = qs.annotate(
            _min_price=Min("details__price"),
            _min_delivery=Min("details__delivery_time_in_days"),
        )

        # Query-Params auslesen
        params = self.request.query_params

        # creator_id
        creator_id = params.get("creator_id")
        if creator_id is not None:
            if not creator_id.isdigit():
                raise ValidationError({"creator_id": "Must be an integer."})
            qs = qs.filter(owner_id=int(creator_id))

        # min_price
        min_price = params.get("min_price")
        if min_price is not None:
            try:
                mp = Decimal(min_price)
            except (InvalidOperation, TypeError):
                raise ValidationError({"min_price": "Must be a number."})
            qs = qs.filter(_min_price__gte=mp)

        # max_delivery_time
        max_delivery_time = params.get("max_delivery_time")
        if max_delivery_time is not None:
            if not max_delivery_time.isdigit():
                raise ValidationError({"max_delivery_time": "Must be an integer."})
            qs = qs.filter(_min_delivery__lte=int(max_delivery_time))

        # search in title/description
        search = params.get("search")
        if search:
            qs = qs.filter(Q(title__icontains=search) | Q(description__icontains=search))

        # ordering: updated_at oder min_price
        ordering = params.get("ordering")
        if ordering:
            allowed = {"updated_at", "min_price", "-updated_at", "-min_price"}
            if ordering not in allowed:
                raise ValidationError(
                    {"ordering": "Allowed values: updated_at, -updated_at, min_price, -min_price."}
                )
            # Map 'min_price' auf annotiertes Feld
            if "min_price" in ordering:
                ordering = ordering.replace("min_price", "_min_price")
            qs = qs.order_by(ordering)
        else:
            # falls nichts angegeben, lass Default-Ordering der Model.Meta oder _min_price
            qs = qs.order_by("-updated_at", "id")

        return qs
    


class OfferRetrieveUpdateDestroyAPIView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET     /api/offers/{id}/
    PATCH   /api/offers/{id}/
    DELETE  /api/offers/{id}/
    """
    queryset = Offer.objects.all().select_related("owner").prefetch_related("details")

    def get_permissions(self):
        if self.request.method in ["PATCH", "PUT", "DELETE"]:
            return [IsAuthenticated(), IsOfferOwner()]
        return [IsAuthenticated()]

    def get_queryset(self):
        return super().get_queryset().annotate(
            _min_price=Min("details__price"),
            _min_delivery=Min("details__delivery_time_in_days"),
        )

    def get_serializer_class(self):
        if self.request.method == "GET":
            return OfferDetailViewSerializer
        if self.request.method in ["PATCH", "PUT"]:
            return OfferPatchSerializer
        return OfferDetailViewSerializer

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", True)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        full = OfferSerializer(instance, context={"request": request})
        return Response(full.data, status=status.HTTP_200_OK)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)


class OfferDetailRetrieveAPIView(generics.RetrieveAPIView):
    """
    GET /api/offerdetails/{id}/
    """
    queryset = OfferDetail.objects.all()
    serializer_class = OfferDetailFullSerializer
    permission_classes = [IsAuthenticated]