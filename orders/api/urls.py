from django.urls import path
from .views import OrderListCreateAPIView, OrderDetailUpdateDeleteAPIView

urlpatterns = [
    path("orders/", OrderListCreateAPIView.as_view(), name="order-create"),
    path("orders/<int:pk>/", OrderDetailUpdateDeleteAPIView.as_view(), name="order-detail"),
]
