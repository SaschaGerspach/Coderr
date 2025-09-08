from django.db import transaction
from rest_framework import serializers

from ..models import Offer, OfferDetail


class OfferDetailSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(read_only=True)

    class Meta:
        model = OfferDetail
        fields = [
            "id",
            "title",
            "revisions",
            "delivery_time_in_days",
            "price",
            "features",
            "offer_type",
        ]

    def validate(self, attrs):
        # price >= 0
        price = attrs.get("price")
        if price is not None and price < 0:
            raise serializers.ValidationError({"price": "Price must be >= 0."})

        # delivery_time_in_days >= 1
        d = attrs.get("delivery_time_in_days")
        if d is not None and d < 1:
            raise serializers.ValidationError(
                {"delivery_time_in_days": "Must be >= 1."}
            )

        # revisions >= 0
        r = attrs.get("revisions")
        if r is not None and r < 0:
            raise serializers.ValidationError(
                {"revisions": "Must be >= 0."}
            )

        # features: Liste von Strings
        features = attrs.get("features")
        if features is None:
            return attrs
        if not isinstance(features, list):
            raise serializers.ValidationError(
                {"features": "Must be an array of strings."}
            )
        if any(not isinstance(x, str) for x in features):
            raise serializers.ValidationError(
                {"features": "All features must be strings."}
            )
        return attrs


class OfferSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(read_only=True)
    details = OfferDetailSerializer(many=True)
    # owner kommt NICHT aus Payload
    title = serializers.CharField(max_length=200)
    image = serializers.URLField(required=False, allow_null=True)
    description = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = Offer
        fields = ["id", "title", "image", "description", "details"]

    def validate_details(self, value):
        if not isinstance(value, list):
            raise serializers.ValidationError("details must be a list.")
        # Genau 3 Details
        if len(value) != 3:
            raise serializers.ValidationError(
                "An offer must contain exactly 3 details."
            )
        # offer_type-Chaos absichern und Einzigartigkeit erzwingen
        types = [d.get("offer_type") for d in value]
        allowed = {c[0] for c in OfferDetail.OfferType.choices}
        if any(t not in allowed for t in types):
            raise serializers.ValidationError(
                "offer_type must be one of: basic, standard, premium."
            )
        if len(set(types)) != len(types):
            raise serializers.ValidationError(
                "Each detail must have a unique offer_type."
            )
        return value

    @transaction.atomic
    def create(self, validated_data):
        details_data = validated_data.pop("details")
        user = self.context["request"].user
        offer = Offer.objects.create(owner=user, **validated_data)
        for d in details_data:
            OfferDetail.objects.create(offer=offer, **d)
        return offer


class OfferDetailMiniSerializer(serializers.ModelSerializer):
    url = serializers.SerializerMethodField()

    class Meta:
        model = OfferDetail
        fields = ["id", "url"]

    def get_url(self, obj):
        # Laut Spec: "/offerdetails/<id>/"
        return f"/offerdetails/{obj.id}/"


class OfferListSerializer(serializers.ModelSerializer):
    # user = Owner-ID
    user = serializers.SerializerMethodField()
    details = OfferDetailMiniSerializer(many=True, read_only=True)
    min_price = serializers.SerializerMethodField()
    min_delivery_time = serializers.SerializerMethodField()
    user_details = serializers.SerializerMethodField()

    class Meta:
        model = Offer
        fields = [
            "id",
            "user",
            "title",
            "image",
            "description",
            "created_at",
            "updated_at",
            "details",
            "min_price",
            "min_delivery_time",
            "user_details",
        ]

    def get_user(self, obj):
        return obj.owner_id
    
    def get_min_price(self, obj):
        v = getattr(obj, "_min_price", None)
        # float sorgt für saubere JSON-Serialisierung (100.0 etc.)
        return float(v) if v is not None else None

    def get_min_delivery_time(self, obj):
        v = getattr(obj, "_min_delivery", None)
        return int(v) if v is not None else None

    def get_user_details(self, obj):
        user = obj.owner
        return {
            "first_name": user.first_name or "",
            "last_name": user.last_name or "",
            "username": user.username or "",
        }
    

class OfferDetailMiniAbsSerializer(serializers.ModelSerializer):
    url = serializers.SerializerMethodField()

    class Meta:
        model = OfferDetail
        fields = ["id", "url"]

    def get_url(self, obj):
        request = self.context.get("request")
        # Spec verlangt absolute URL im Detail-Endpoint
        if request:
            return request.build_absolute_uri(f"/api/offerdetails/{obj.id}/")
        return f"/api/offerdetails/{obj.id}/"
        

class OfferDetailViewSerializer(serializers.ModelSerializer):
    user = serializers.SerializerMethodField()
    # wichtig: hier die *absolute* Variante nutzen
    details = OfferDetailMiniAbsSerializer(many=True, read_only=True)
    min_price = serializers.SerializerMethodField()
    min_delivery_time = serializers.SerializerMethodField()

    class Meta:
        model = Offer
        fields = [
            "id",
            "user",
            "title",
            "image",
            "description",
            "created_at",
            "updated_at",
            "details",
            "min_price",
            "min_delivery_time",
        ]

    def get_user(self, obj):
        return obj.owner_id

    def get_min_price(self, obj):
        v = getattr(obj, "_min_price", None)
        return float(v) if v is not None else None

    def get_min_delivery_time(self, obj):
        v = getattr(obj, "_min_delivery", None)
        return int(v) if v is not None else None


