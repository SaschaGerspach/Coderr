from django.urls import path
from .views import OfferCreateAPIView

urlpatterns = [
    path("offers/", OfferCreateAPIView.as_view(), name="offer-create"),
]
