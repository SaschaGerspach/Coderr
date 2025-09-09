from django.urls import path
from .views import OrderListCreateAPIView, OrderStatusUpdateAPIView

urlpatterns = [
    path("orders/", OrderListCreateAPIView.as_view(), name="order-create"),
    path("orders/<int:pk>/", OrderStatusUpdateAPIView.as_view(), name="order-detail"),
]
