"""Orders API serializers.

Input/Output serializers for creating orders from offer details, representing
orders to clients, and patching order status. Validation ensures that users
cannot order their own offers and that referenced OfferDetail exists.
"""

from rest_framework import serializers
from rest_framework.exceptions import PermissionDenied
from offers.models import OfferDetail
from orders.models import Order


class OrderCreateSerializer(serializers.Serializer):
    """Input serializer for creating an order from an OfferDetail id.

    Validates:
    - offer_detail_id exists (404-like validation error if not found)
    - the authenticated user is not the owner (business) of the referenced offer
    """

    offer_detail_id = serializers.IntegerField(required=True)

    def validate_offer_detail_id(self, value):
        """Ensure the OfferDetail exists and store it in the serializer context."""
        try:
            offeredetail = OfferDetail.objects.select_related(
                "offer", "offer__owner"
            ).get(id=value)
        except OfferDetail.DoesNotExist:
            raise serializers.ValidationError("OfferDetail not found.")
        self.context["offerdetail_obj"] = offeredetail
        return value

    def validate(self, attrs):
        """Prevent users from ordering their own offers; require authentication."""
        request = self.context.get("request")
        offeredetail = self.context.get("offerdetail_obj")
        if not request or not request.user.is_authenticated:
            # 401 is handled by permission; kept as fallback
            raise serializers.ValidationError("Authentication required.")
        business_user = offeredetail.offer.owner
        if request.user.id == business_user.id:
            # Customers must not order their own offers
            raise PermissionDenied("You cannot order your own offer.")
        return attrs

    def create(self, validated_data):
        """Create the order by snapshotting fields from the OfferDetail."""
        request = self.context["request"]
        od = self.context["offerdetail_obj"]
        order = Order.objects.create(
            customer_user=request.user,
            business_user=od.offer.owner,
            offer_detail=od,
            title=od.title,
            revisions=od.revisions,
            delivery_time_in_days=od.delivery_time_in_days,
            price=od.price,
            features=od.features or [],
            offer_type=od.offer_type,
            status=Order.Status.IN_PROGRESS,
        )
        return order


class OrderOutputSerializer(serializers.ModelSerializer):
    """Read serializer for returning a complete order representation."""

    class Meta:
        model = Order
        fields = [
            "id",
            "customer_user",
            "business_user",
            "title",
            "revisions",
            "delivery_time_in_days",
            "price",
            "features",
            "offer_type",
            "status",
            "created_at",
            "updated_at",
        ]


class OrderStatusPatchSerializer(serializers.ModelSerializer):
    """Patch serializer used to update only the order status."""

    class Meta:
        model = Order
        fields = ["status"]
