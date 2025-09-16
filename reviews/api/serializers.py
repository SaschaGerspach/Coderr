"""Reviews API serializers.

Provide serializers for creating a review, returning review data, and
partially updating rating/description. Enforces one review per (business_user, reviewer)
and validates target user is a business.
"""

from django.contrib.auth import get_user_model
from rest_framework import serializers

from reviews.models import Review

User = get_user_model()


class ReviewCreateSerializer(serializers.Serializer):
    """Input serializer for creating a new review."""

    business_user = serializers.IntegerField(required=True)
    rating = serializers.IntegerField(min_value=1, max_value=5, required=True)
    description = serializers.CharField(allow_blank=True, required=False, default="")

    def validate_business_user(self, value):
        """Ensure the target user exists and has a business profile."""
        try:
            user = User.objects.select_related("profile").get(id=value)
        except User.DoesNotExist:
            raise serializers.ValidationError("Business user not found.")

        profile = getattr(user, "profile", None)
        if not profile or getattr(profile, "type", "") != "business":
            raise serializers.ValidationError("Target user is not a business.")

        self.context["business_user_obj"] = user
        return value

    def validate(self, attrs):
        """Ensure the reviewer is authenticated, not reviewing self, and hasn't reviewed before."""
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            # Fallback; IsAuthenticated on the view is the primary guard.
            raise serializers.ValidationError("Authentication required.")

        business_user = self.context.get("business_user_obj")
        reviewer = request.user

        if business_user.id == reviewer.id:
            raise serializers.ValidationError(
                {"business_user": "You cannot review yourself."}
            )

        exists = Review.objects.filter(
            business_user=business_user, reviewer=reviewer
        ).exists()
        if exists:
            raise serializers.ValidationError(
                {"non_field_errors": ["You have already reviewed this business user."]}
            )
        return attrs

    def create(self, validated_data):
        """Create and return the review instance."""
        business_user = self.context["business_user_obj"]
        reviewer = self.context["request"].user
        return Review.objects.create(
            business_user=business_user,
            reviewer=reviewer,
            rating=validated_data["rating"],
            description=validated_data.get("description", "") or "",
        )


class ReviewOutputSerializer(serializers.ModelSerializer):
    """Read serializer for returning a review."""

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
    """Patch serializer for updating rating/description only."""

    class Meta:
        model = Review
        fields = ["rating", "description"]
