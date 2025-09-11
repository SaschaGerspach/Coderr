from django.urls import path
from .views import ReviewListCreateAPIView, ReviewDetailUpdateDeleteAPIView

urlpatterns = [
    path("reviews/", ReviewListCreateAPIView.as_view(), name="review-create"),
    path("reviews/<int:pk>/", ReviewDetailUpdateDeleteAPIView.as_view(), name="review-detail"),
]
