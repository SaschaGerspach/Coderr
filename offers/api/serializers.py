"""Offers API serializers.

Provide serializers for creating offers (with nested details), listing offers,
retrieving a single offer (with computed fields), partially updating an offer
(details identified by offer_type), and retrieving a single OfferDetail.
"""

from decimal import Decimal
from django.db import transaction
from rest_framework import serializers

from ..models import Offer, OfferDetail


# --------------------------- helpers (pure functions) ---------------------------

def _ensure_features_is_str_list(features):
    if not isinstance(features, list):
        raise serializers.ValidationError({"features": "Must be an array of strings."})
    if any(not isinstance(x, str) for x in features):
        raise serializers.ValidationError({"features": "All features must be strings."})


def _validate_non_negative(value, field, min_allowed=0):
    if value is not None and value < min_allowed:
        bound = ">=" if min_allowed == 0 else f">= {min_allowed}"
        raise serializers.ValidationError({field: f"Must be {bound}."})


def _extract_annotated(obj, attr, caster):
    v = getattr(obj, attr, None)
    return caster(v) if v is not None else None


# --------------------------------- serializers ---------------------------------

class OfferDetailSerializer(serializers.ModelSerializer):
    """Nested serializer for OfferDetail during offer creation."""

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
        """Validate numeric lower bounds and ensure features is a list of strings."""
        _validate_non_negative(attrs.get("price"), "price", 0)
        _validate_non_negative(attrs.get("delivery_time_in_days"), "delivery_time_in_days", 1)
        _validate_non_negative(attrs.get("revisions"), "revisions", 0)

        features = attrs.get("features", None)
        if features is not None:
            _ensure_features_is_str_list(features)
        return attrs


class OfferSerializer(serializers.ModelSerializer):
    """Serializer for creating an offer with exactly three nested details.

    Notes:
    - The owner is taken from request.user (context) and never from payload.
    - details must contain exactly one entry per offer_type (basic/standard/premium).
    """

    id = serializers.IntegerField(read_only=True)
    details = OfferDetailSerializer(many=True)
    title = serializers.CharField(max_length=200)
    image = serializers.URLField(required=False, allow_null=True)
    description = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = Offer
        fields = ["id", "title", "image", "description", "details"]

    def validate_details(self, value):
        """Ensure there are exactly three details and unique, valid offer_type values."""
        if not isinstance(value, list):
            raise serializers.ValidationError("details must be a list.")
        if len(value) != 3:
            raise serializers.ValidationError("An offer must contain exactly 3 details.")

        types = [d.get("offer_type") for d in value]
        allowed = {c[0] for c in OfferDetail.OfferType.choices}
        if any(t not in allowed for t in types):
            raise serializers.ValidationError("offer_type must be one of: basic, standard, premium.")
        if len(set(types)) != len(types):
            raise serializers.ValidationError("Each detail must have a unique offer_type.")
        return value

    @transaction.atomic
    def create(self, validated_data):
        """Create the Offer and its three OfferDetail rows in a single transaction."""
        details_data = validated_data.pop("details")
        user = self.context["request"].user
        offer = Offer.objects.create(owner=user, **validated_data)
        for d in details_data:
            OfferDetail.objects.create(offer=offer, **d)
        return offer


class OfferDetailMiniSerializer(serializers.ModelSerializer):
    """Minimal representation of an OfferDetail, used in list views."""

    url = serializers.SerializerMethodField()

    class Meta:
        model = OfferDetail
        fields = ["id", "url"]

    def get_url(self, obj):
        # Spec requires a relative URL: "/offerdetails/<id>/"
        return f"/offerdetails/{obj.id}/"


class OfferListSerializer(serializers.ModelSerializer):
    """List serializer for offers including minimal details and computed fields."""

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
        return _extract_annotated(obj, "_min_price", float)

    def get_min_delivery_time(self, obj):
        return _extract_annotated(obj, "_min_delivery", int)

    def get_user_details(self, obj):
        u = obj.owner
        return {"first_name": u.first_name or "", "last_name": u.last_name or "", "username": u.username or ""}


class OfferDetailMiniAbsSerializer(serializers.ModelSerializer):
    """Minimal representation of an OfferDetail with absolute URLs (detail view)."""

    url = serializers.SerializerMethodField()

    class Meta:
        model = OfferDetail
        fields = ["id", "url"]

    def get_url(self, obj):
        # Spec for detail endpoint: absolute URL
        request = self.context.get("request")
        return request.build_absolute_uri(f"/api/offerdetails/{obj.id}/") if request else f"/api/offerdetails/{obj.id}/"


class OfferDetailViewSerializer(serializers.ModelSerializer):
    """Detail serializer for an offer including minimal absolute detail links."""

    user = serializers.SerializerMethodField()
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
        return _extract_annotated(obj, "_min_price", float)

    def get_min_delivery_time(self, obj):
        return _extract_annotated(obj, "_min_delivery", int)


class OfferDetailPartialSerializer(serializers.Serializer):
    """Serializer for a single detail update in PATCH.

    Identification:
    - `offer_type` is required (one of: basic/standard/premium).
    - Optional `id` may be provided; if present, it must match the resolved detail.

    Rules:
    - Only provided fields are updated.
    - `offer_type` itself cannot be changed.
    """

    id = serializers.IntegerField(required=False)
    offer_type = serializers.ChoiceField(choices=[c[0] for c in OfferDetail.OfferType.choices])
    title = serializers.CharField(max_length=200, required=False)
    revisions = serializers.IntegerField(min_value=0, required=False)
    delivery_time_in_days = serializers.IntegerField(min_value=1, required=False)
    price = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=Decimal("0"), required=False)
    features = serializers.ListField(child=serializers.CharField(), required=False)

    def validate_features(self, v):
        """Ensure features is a list of strings."""
        _ensure_features_is_str_list(v)
        return v


class OfferPatchSerializer(serializers.ModelSerializer):
    """PATCH serializer for offers, allowing partial update of offer and details.

    - Offer fields: title, image, description (all optional).
    - Details: list of partial updates, each identified by `offer_type`.
    - After update, the view returns the full offer using a dedicated serializer.
    """

    details = OfferDetailPartialSerializer(many=True, required=False)

    class Meta:
        model = Offer
        fields = ["title", "image", "description", "details"]
        extra_kwargs = {
            "image": {"required": False, "allow_null": True},
            "description": {"required": False, "allow_blank": True},
        }

    def validate(self, attrs):
        """Hook kept for symmetry; spec does not impose additional constraints."""
        return attrs

    # ------------------------- private helpers (update) -------------------------

    def _update_offer_fields(self, instance: Offer, data: dict) -> None:
        changed = False
        for f in ("title", "image", "description"):
            if f in data:
                setattr(instance, f, data[f])
                changed = True
        if changed:
            instance.save()

    def _require_detail_for_type(self, instance: Offer, offer_type: str) -> OfferDetail:
        detail = {d.offer_type: d for d in instance.details.all()}.get(offer_type)
        if detail is None:
            raise serializers.ValidationError(
                {"details": f"Detail with offer_type '{offer_type}' does not exist for this offer."}
            )
        return detail

    def _apply_detail_patch(self, detail: OfferDetail, payload: dict) -> None:
        if "id" in payload and payload["id"] != detail.id:
            raise serializers.ValidationError({"details": f"Detail id mismatch for offer_type '{detail.offer_type}'."})
        fields = [f for f in ("title", "revisions", "delivery_time_in_days", "price", "features") if f in payload]
        for f in fields:
            setattr(detail, f, payload[f])
        if fields:
            detail.save(update_fields=fields)

    def _apply_details_updates(self, instance: Offer, details_updates) -> None:
        for payload in details_updates:
            offer_type = payload.get("offer_type")
            if not offer_type:
                raise serializers.ValidationError({"details": "Each detail must include offer_type."})
            detail = self._require_detail_for_type(instance, offer_type)
            self._apply_detail_patch(detail, payload)

    # --------------------------------- update ----------------------------------

    @transaction.atomic
    def update(self, instance: Offer, validated_data):
        """Apply partial updates to offer and its existing details."""
        details_updates = validated_data.pop("details", None)
        self._update_offer_fields(instance, validated_data)
        if details_updates:
            self._apply_details_updates(instance, details_updates)
        return instance


class OfferDetailFullSerializer(serializers.ModelSerializer):
    """Full serializer for a single OfferDetail (detail endpoint)."""

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
