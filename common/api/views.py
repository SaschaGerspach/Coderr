from django.db.models import Avg
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status

from reviews.models import Review
from profiles.models import Profile
from offers.models import Offer


class BaseInfoAPIView(APIView):
    """
    GET /api/base-info/

    Returns platform-wide aggregate statistics:
    - review_count: total number of reviews
    - average_rating: average rating across all reviews (rounded to 1 decimal)
    - business_profile_count: number of profiles with type="business"
    - offer_count: total number of offers

    Authentication: none
    Permissions: AllowAny
    """

    authentication_classes = []          # No authentication required
    permission_classes = [AllowAny]      # Explicitly allow public access

    def get(self, request):
        """
        Compute and return the aggregate counters. If there are no reviews,
        average_rating is 0.0 (not null).
        """
        try:
            review_count = Review.objects.count()
            avg = Review.objects.aggregate(avg=Avg("rating"))["avg"] or 0.0
            average_rating = round(float(avg), 1)

            business_profile_count = Profile.objects.filter(type="business").count()
            offer_count = Offer.objects.count()

            data = {
                "review_count": review_count,
                "average_rating": average_rating,
                "business_profile_count": business_profile_count,
                "offer_count": offer_count,
            }
            return Response(data, status=status.HTTP_200_OK)
        except Exception:
            # Keep the response surface simple per spec.
            return Response(
                {"detail": "Internal Server Error"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
