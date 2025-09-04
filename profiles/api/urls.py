from django.urls import path
from .views import ProfileView, BusinessProfileListView

urlpatterns = [
    path("profile/<int:pk>/", ProfileView.as_view(), name="profile"),
    path("profiles/business/", BusinessProfileListView.as_view(), name="business-profiles"),
]
