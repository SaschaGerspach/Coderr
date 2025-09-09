from django.urls import path
from .views import OfferListCreateAPIView, OfferRetrieveUpdateDestroyAPIView

urlpatterns = [
    path("offers/", OfferListCreateAPIView.as_view(), name="offer-create"),
    path("offers/<int:pk>/", OfferRetrieveUpdateDestroyAPIView.as_view(), name="offer-detail"),
]
