from django.urls import path
from .views import OfferListCreateAPIView

urlpatterns = [
    path("offers/", OfferListCreateAPIView.as_view(), name="offer-create"),
]
