from django.contrib.auth import get_user_model
from django.db.models import Q
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError

from reviews.models import Review
from .serializers import ReviewCreateSerializer, ReviewOutputSerializer, ReviewPatchSerializer
from .permissions import IsCustomerReviewer, IsReviewOwner

User = get_user_model()


class ReviewListCreateAPIView(generics.ListCreateAPIView):
    """
    GET  /api/reviews/  -> Liste aller Reviews (auth-pflichtig),
                          Filter: business_user_id, reviewer_id
                          Ordering: updated_at, -updated_at, rating, -rating
    POST /api/reviews/  -> wie zuvor (nur customer, reviewer= request.user)
    """
    queryset = Review.objects.all().select_related("business_user", "reviewer")

    def get_permissions(self):
        if self.request.method == "POST":
            return [IsAuthenticated(), IsCustomerReviewer()]
        return [IsAuthenticated()]

    def get_serializer_class(self):
        return ReviewOutputSerializer if self.request.method == "GET" else ReviewCreateSerializer

    # --- GET ---
    def get_queryset(self):
        qs = super().get_queryset()
        params = self.request.query_params

        # Filter: business_user_id
        business_user_id = params.get("business_user_id")
        if business_user_id:
            if not business_user_id.isdigit():
                raise ValidationError({"business_user_id": "Must be an integer."})
            qs = qs.filter(business_user_id=int(business_user_id))

        # Filter: reviewer_id
        reviewer_id = params.get("reviewer_id")
        if reviewer_id:
            if not reviewer_id.isdigit():
                raise ValidationError({"reviewer_id": "Must be an integer."})
            qs = qs.filter(reviewer_id=int(reviewer_id))

        # Ordering
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

    # --- POST (unverändert) ---
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        review = serializer.save()
        out = ReviewOutputSerializer(review)
        return Response(out.data, status=status.HTTP_201_CREATED)


class ReviewDetailUpdateDeleteAPIView(generics.RetrieveUpdateDestroyAPIView):
    """
    PATCH /api/reviews/{id}/  -> nur rating/description (nur Owner)
    DELETE /api/reviews/{id}/ -> nur Owner

    """
    queryset = Review.objects.all().select_related("business_user", "reviewer")
    permission_classes = [IsAuthenticated, IsReviewOwner]
    
    def get_serializer_class(self):
        if self.request.method == "PATCH":
            return ReviewPatchSerializer
        return ReviewOutputSerializer

    def partial_update(self, request, *args, **kwargs):
        # Nur diese Keys sind erlaubt:
        allowed = {"rating", "description"}
        extra = set(request.data.keys()) - allowed
        if extra:
            return Response(
                {"detail": f"Only 'rating' and 'description' may be updated. Invalid: {', '.join(sorted(extra))}."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(ReviewOutputSerializer(instance).data, status=status.HTTP_200_OK)

    # PATCH ruft update(); wir erzwingen partial=True
    def update(self, request, *args, **kwargs):
        kwargs["partial"] = True
        return self.partial_update(request, *args, **kwargs)
    
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)