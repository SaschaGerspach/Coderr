from django.contrib.auth import get_user_model
from rest_framework import serializers
from reviews.models import Review

User = get_user_model()


class ReviewCreateSerializer(serializers.Serializer):
    business_user = serializers.IntegerField(required=True)
    rating = serializers.IntegerField(min_value=1, max_value=5, required=True)
    description = serializers.CharField(allow_blank=True, required=False, default="")

    def validate_business_user(self, value):
        # Existiert der User?
        try:
            user = User.objects.select_related("profile").get(id=value)
        except User.DoesNotExist:
            raise serializers.ValidationError("Business user not found.")
        # Muss Business-Profil haben
        prof = getattr(user, "profile", None)
        if not prof or getattr(prof, "type", "") != "business":
            raise serializers.ValidationError("Target user is not a business.")
        self.context["business_user_obj"] = user
        return value

    def validate(self, attrs):
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            # Fallback – eig. handled durch Permission
            raise serializers.ValidationError("Authentication required.")

        business_user = self.context.get("business_user_obj")
        reviewer = request.user

        # Reviewer darf sich nicht selbst reviewen (sollte mit Typen ohnehin ausgeschlossen sein)
        if business_user.id == reviewer.id:
            raise serializers.ValidationError({"business_user": "You cannot review yourself."})

        # Ein Review pro (business_user, reviewer)
        if Review.objects.filter(business_user=business_user, reviewer=reviewer).exists():
            raise serializers.ValidationError(
                {"non_field_errors": ["You have already reviewed this business user."]}
            )
        return attrs

    def create(self, validated_data):
        business_user = self.context["business_user_obj"]
        reviewer = self.context["request"].user
        review = Review.objects.create(
            business_user=business_user,
            reviewer=reviewer,
            rating=validated_data["rating"],
            description=validated_data.get("description", "") or "",
        )
        return review


class ReviewOutputSerializer(serializers.ModelSerializer):
    class Meta:
        model = Review
        fields = [
            "id",
            "business_user",
            "reviewer",
            "rating",
            "description",
            "created_at",
            "updated_at",
        ]


class ReviewPatchSerializer(serializers.ModelSerializer):
    class Meta:
        model = Review
        fields = ["rating", "description"] 