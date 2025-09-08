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
