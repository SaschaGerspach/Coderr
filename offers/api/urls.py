from django.urls import path
from .views import OfferListCreateAPIView, OfferRetrieveUpdateAPIView

urlpatterns = [
    path("offers/", OfferListCreateAPIView.as_view(), name="offer-create"),
    path("offers/<int:pk>/", OfferRetrieveUpdateAPIView.as_view(), name="offer-detail"),
]
