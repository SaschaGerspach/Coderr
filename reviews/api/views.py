from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from reviews.models import Review
from .serializers import ReviewCreateSerializer, ReviewOutputSerializer
from .permissions import IsCustomerReviewer


class ReviewCreateAPIView(generics.CreateAPIView):
    """
    POST /api/reviews/
    Nur authentifizierte Customer dürfen erstellen.
    """
    queryset = Review.objects.all()
    serializer_class = ReviewCreateSerializer
    permission_classes = [IsAuthenticated, IsCustomerReviewer]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        review = serializer.save()
        out = ReviewOutputSerializer(review)
        return Response(out.data, status=status.HTTP_201_CREATED)
