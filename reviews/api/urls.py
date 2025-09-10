from django.urls import path
from .views import ReviewCreateAPIView

urlpatterns = [
    path("reviews/", ReviewCreateAPIView.as_view(), name="review-create"),
]
