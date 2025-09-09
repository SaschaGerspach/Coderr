from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase
from django.db import models

from profiles.models import Profile
from offers.models import Offer, OfferDetail


User = get_user_model()


def create_profile_with_type(user, target: str):
    p = Profile.objects.create(user=user)
    for f in p._meta.fields:
        if isinstance(f, models.CharField) and getattr(f, "choices", None):
            allowed = {c[0] for c in f.choices}
            if target in allowed:
                setattr(p, f.name, target)
                p.save(update_fields=[f.name])
                return p
    if target == "business":
        for name in ["is_business", "business", "is_vendor"]:
            if hasattr(p, name):
                setattr(p, name, True)
                p.save(update_fields=[name])
                return p
    raise AssertionError("Kein passendes Profil-Feld gefunden")


class OfferDetailRetrieveTests(APITestCase):
    def setUp(self):
        # User
        self.user = User.objects.create_user("user", "user@example.com", "pass1234")
        create_profile_with_type(self.user, "business")
        self.token = Token.objects.create(user=self.user)

        # Angebot + Detail
        self.offer = Offer.objects.create(owner=self.user, title="Test", description="desc")
        self.detail = OfferDetail.objects.create(
            offer=self.offer,
            title="Basic Design",
            revisions=2,
            delivery_time_in_days=5,
            price="100.00",
            features=["Logo", "Visitenkarte"],
            offer_type="basic",
        )
        self.url = reverse("offerdetail-detail", args=[self.detail.id])

    def auth(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token.key}")

    def test_retrieve_success_200(self):
        self.auth()
        res = self.client.get(self.url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["id"], self.detail.id)
        self.assertEqual(res.data["title"], "Basic Design")
        self.assertEqual(res.data["price"], "100.00")
        self.assertEqual(res.data["offer_type"], "basic")

    def test_unauthenticated_returns_401(self):
        res = self.client.get(self.url)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_not_found_returns_404(self):
        self.auth()
        url = reverse("offerdetail-detail", args=[999999])
        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)
