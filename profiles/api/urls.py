from django.urls import path
from .views import ProfilePartialUpdateView

urlpatterns = [
    path("profile/<int:pk>/", ProfilePartialUpdateView.as_view(), name="profile-partial-update"),
]
