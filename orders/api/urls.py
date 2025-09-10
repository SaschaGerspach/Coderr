from django.urls import path
from .views import OrderListCreateAPIView, OrderDetailUpdateDeleteAPIView, OrderCountAPIView

urlpatterns = [
    path("orders/", OrderListCreateAPIView.as_view(), name="order-create"),
    path("orders/<int:pk>/", OrderDetailUpdateDeleteAPIView.as_view(), name="order-detail"),
    path("order-count/<int:business_user_id>/", OrderCountAPIView.as_view(), name="order-count"),
]
