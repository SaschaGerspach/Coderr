from rest_framework import serializers
from rest_framework.exceptions import PermissionDenied
from offers.models import OfferDetail
from orders.models import Order


class OrderCreateSerializer(serializers.Serializer):
    offer_detail_id = serializers.IntegerField(required=True)

    def validate_offer_detail_id(self, value):
        try:
            offeredetail = OfferDetail.objects.select_related("offer", "offer__owner").get(id=value)
        except OfferDetail.DoesNotExist:
            raise serializers.ValidationError("OfferDetail not found.")
        self.context["offerdetail_obj"] = offeredetail
        return value

    def validate(self, attrs):
        request = self.context.get("request")
        offeredetail = self.context.get("offerdetail_obj")
        if not request or not request.user.is_authenticated:
            # 401 handled by permission, hier nur als Fallback
            raise serializers.ValidationError("Authentication required.")
        # Business des Offers:
        business_user = offeredetail.offer.owner
        # Kunde = request.user
        if request.user.id == business_user.id:
            # Kunde darf nicht sein eigenes Angebot bestellen
            raise PermissionDenied("You cannot order your own offer.")
        return attrs

    def create(self, validated_data):
        request = self.context["request"]
        od = self.context["offerdetail_obj"]
        # Snapshot der relevanten Felder aus OfferDetail
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
    class Meta:
        model = Order
        fields = ["status"] 