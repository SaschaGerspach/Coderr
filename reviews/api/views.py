"""Reviews API views.

List and create reviews on the same endpoint (auth required). Supports filtering
by business_user_id and reviewer_id and ordering by updated_at or rating.
Retrieve/patch/delete a single review with owner-only modifications.
"""

from django.contrib.auth import get_user_model
from rest_framework import generics, status
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from reviews.models import Review
from .permissions import IsCustomerReviewer, IsReviewOwner
from .serializers import (
    ReviewCreateSerializer,
    ReviewOutputSerializer,
    ReviewPatchSerializer,
)

User = get_user_model()


# ----------------------------- helpers (module-level) -----------------------------

def _apply_filters_and_ordering(qs, params):
    """Filter by ids and apply ordering; raises ValidationError on bad input."""
    # business_user_id
    v = params.get("business_user_id")
    if v:
        if not v.isdigit():
            raise ValidationError({"business_user_id": "Must be an integer."})
        qs = qs.filter(business_user_id=int(v))

    # reviewer_id
    v = params.get("reviewer_id")
    if v:
        if not v.isdigit():
            raise ValidationError({"reviewer_id": "Must be an integer."})
        qs = qs.filter(reviewer_id=int(v))

    # ordering
    ordering = params.get("ordering")
    if ordering:
        allowed = {"updated_at", "-updated_at", "rating", "-rating"}
        if ordering not in allowed:
            raise ValidationError(
                {"ordering": "Allowed values: updated_at, -updated_at, rating, -rating."}
            )
        qs = qs.order_by(ordering)
    else:
        qs = qs.order_by("-updated_at", "-id")

    return qs


def _validate_patch_fields(data: dict):
    """Allow only rating/description; return Response(400) if extra fields present."""
    allowed = {"rating", "description"}
    extra = set(data.keys()) - allowed
    if extra:
        return Response(
            {
                "detail": (
                    "Only 'rating' and 'description' may be updated. "
                    f"Invalid: {', '.join(sorted(extra))}."
                )
            },
            status=status.HTTP_400_BAD_REQUEST,
        )
    return None


# --------------------------------------- views ---------------------------------------

class ReviewListCreateAPIView(generics.ListCreateAPIView):
    """GET: list reviews (filter/order). POST: create review (customer-only)."""

    queryset = Review.objects.all().select_related("business_user", "reviewer")

    def get_permissions(self):
        """Customer-only for POST; otherwise authenticated read."""
        if self.request.method == "POST":
            return [IsAuthenticated(), IsCustomerReviewer()]
        return [IsAuthenticated()]

    def get_serializer_class(self):
        """Use output serializer for GET and create serializer for POST."""
        return ReviewOutputSerializer if self.request.method == "GET" else ReviewCreateSerializer

    # --- GET ---
    def get_queryset(self):
        """Apply optional filters and ordering from query parameters."""
        return _apply_filters_and_ordering(super().get_queryset(), self.request.query_params)

    # --- POST ---
    def create(self, request, *args, **kwargs):
        """Validate and create a review; return the created representation."""
        ser = self.get_serializer(data=request.data, context={"request": request})
        ser.is_valid(raise_exception=True)
        review = ser.save()
        return Response(ReviewOutputSerializer(review).data, status=status.HTTP_201_CREATED)


class ReviewDetailUpdateDeleteAPIView(generics.RetrieveUpdateDestroyAPIView):
    """PATCH: owner-only update of rating/description. DELETE: owner-only delete."""

    queryset = Review.objects.all().select_related("business_user", "reviewer")
    permission_classes = [IsAuthenticated, IsReviewOwner]

    def get_serializer_class(self):
        """Use patch serializer for PATCH; output serializer otherwise."""
        return ReviewPatchSerializer if self.request.method == "PATCH" else ReviewOutputSerializer

    def partial_update(self, request, *args, **kwargs):
        """Allow updating only 'rating' and 'description'; return full review."""
        bad = _validate_patch_fields(request.data)
        if bad is not None:
            return bad
        instance = self.get_object()
        ser = self.get_serializer(instance, data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        self.perform_update(ser)
        return Response(ReviewOutputSerializer(instance).data, status=status.HTTP_200_OK)

    def update(self, request, *args, **kwargs):
        """Force partial updates via PATCH semantics."""
        kwargs["partial"] = True
        return self.partial_update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        """Delete the review (owner-only) and return 204 No Content."""
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)
