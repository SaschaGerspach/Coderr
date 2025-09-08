from decimal import Decimal
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


class OfferDetailPartialSerializer(serializers.Serializer):
    """
    Serializer für EIN Detail-Update in PATCH.
    - offer_type: Pflicht zur Identifikation (basic/standard/premium)
    - alle anderen Felder optional (partial update)
    - 'id' darf mitgegeben werden, MUSS aber zum gefundenen Detail passen, sonst 400
    """
    id = serializers.IntegerField(required=False)
    offer_type = serializers.ChoiceField(choices=[c[0] for c in OfferDetail.OfferType.choices])
    title = serializers.CharField(max_length=200, required=False)
    revisions = serializers.IntegerField(min_value=0, required=False)
    delivery_time_in_days = serializers.IntegerField(min_value=1, required=False)
    price = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=Decimal("0"), required=False)
    features = serializers.ListField(
        child=serializers.CharField(), required=False
    )

    def validate_features(self, v):
        # leere Liste ist erlaubt, None kommt hier nicht an, weil required=False
        if not isinstance(v, list):
            raise serializers.ValidationError("features must be an array of strings.")
        for x in v:
            if not isinstance(x, str):
                raise serializers.ValidationError("All features must be strings.")
        return v


class OfferPatchSerializer(serializers.ModelSerializer):
    """
    PATCH-Serializer für Offer:
    - erlaubt partielle Updates an Offer-Feldern (title, image, description)
    - 'details' kann eine Liste von Änderungen enthalten; jede Änderung referenziert per offer_type
    - nach update() geben wir das vollständige Offer (mit allen Details) über den View zurück
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
        # Kein spezielles Offer-Validierungs-Requirement über die Spec hinaus
        return attrs

    @transaction.atomic
    def update(self, instance: Offer, validated_data):
        details_updates = validated_data.pop("details", None)

        # 1) Offer-Felder partiell setzen
        for field in ["title", "image", "description"]:
            if field in validated_data:
                setattr(instance, field, validated_data[field])
        instance.save()

        # 2) Details partiell updaten (falls mitgegeben)
        if details_updates:
            # Map vorhandene Details nach offer_type
            existing_by_type = {d.offer_type: d for d in instance.details.all()}

            for payload in details_updates:
                offer_type = payload.get("offer_type")
                if not offer_type:
                    raise serializers.ValidationError({"details": "Each detail must include offer_type."})

                detail = existing_by_type.get(offer_type)
                if detail is None:
                    raise serializers.ValidationError(
                        {"details": f"Detail with offer_type '{offer_type}' does not exist for this offer."}
                    )

                # Wenn eine 'id' mitkommt, muss sie zum gefundenen Detail passen
                if "id" in payload and payload["id"] != detail.id:
                    raise serializers.ValidationError(
                        {"details": f"Detail id mismatch for offer_type '{offer_type}'."}
                    )

                # 'offer_type' selbst darf nicht geändert werden (wird ignoriert)
                update_fields = {}
                for f in ["title", "revisions", "delivery_time_in_days", "price", "features"]:
                    if f in payload:
                        setattr(detail, f, payload[f])
                        update_fields[f] = True

                if update_fields:
                    # nur geänderte Felder speichern
                    detail.save(update_fields=list(update_fields.keys()))

        # Rückgabe der aktualisierten Instanz – die View serialisiert mit dem Voll-Serializer
        return instance