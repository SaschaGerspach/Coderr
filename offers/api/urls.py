from django.urls import path
from .views import OfferListCreateAPIView, OfferRetrieveAPIView

urlpatterns = [
    path("offers/", OfferListCreateAPIView.as_view(), name="offer-create"),
    path("offers/<int:pk>/", OfferRetrieveAPIView.as_view(), name="offer-detail"),
]
