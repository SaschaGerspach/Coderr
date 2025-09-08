from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework.authtoken.models import Token

from profiles.models import Profile
from offers.models import Offer, OfferDetail
from django.db import models


User = get_user_model()


def create_profile_with_type(user, target: str):
    p = Profile.objects.create(user=user)
    # Versuche CharField mit Choices
    for f in p._meta.fields:
        if isinstance(f, models.CharField) and getattr(f, "choices", None):
            allowed = {c[0] for c in f.choices}
            if target in allowed:
                setattr(p, f.name, target)
                p.save(update_fields=[f.name])
                return p
    # Fallback für Bool-Felder
    if target == "business":
        for name in ["is_business", "business", "is_vendor"]:
            if hasattr(p, name):
                setattr(p, name, True)
                p.save(update_fields=[name])
                return p
    raise AssertionError("Kein passendes Profil-Feld gefunden")


def add_offer(user):
    offer = Offer.objects.create(owner=user, title="Test Offer", description="desc")
    OfferDetail.objects.create(
        offer=offer, title="Basic", revisions=1,
        delivery_time_in_days=5, price="50.00", features=["x"], offer_type="basic"
    )
    OfferDetail.objects.create(
        offer=offer, title="Standard", revisions=2,
        delivery_time_in_days=7, price="100.00", features=["y"], offer_type="standard"
    )
    OfferDetail.objects.create(
        offer=offer, title="Premium", revisions=3,
        delivery_time_in_days=10, price="200.00", features=["z"], offer_type="premium"
    )
    return offer


class OfferDetailTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user("biz", "biz@example.com", "pass1234")
        create_profile_with_type(self.user, "business")
        self.token = Token.objects.create(user=self.user)

        self.offer = add_offer(self.user)
        self.url = reverse("offer-detail", args=[self.offer.id])

    def auth(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token.key}")

    def test_retrieve_offer_authenticated(self):
        self.auth()
        res = self.client.get(self.url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["id"], self.offer.id)
        self.assertEqual(res.data["user"], self.user.id)
        self.assertIn("details", res.data)
        self.assertEqual(len(res.data["details"]), 3)
        self.assertEqual(float(res.data["min_price"]), 50.0)
        self.assertEqual(int(res.data["min_delivery_time"]), 5)

    def test_unauthenticated_returns_401(self):
        res = self.client.get(self.url)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_invalid_offer_returns_404(self):
        self.auth()
        bad_url = reverse("offer-detail", args=[9999])
        res = self.client.get(bad_url)
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)
