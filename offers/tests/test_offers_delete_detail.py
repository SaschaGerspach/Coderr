from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase
from django.db import models

from profiles.models import Profile
from offers.models import Offer


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


class OfferDeleteTests(APITestCase):
    def setUp(self):
        # Owner
        self.owner = User.objects.create_user("owner", "owner@example.com", "pass1234")
        create_profile_with_type(self.owner, "business")
        self.owner_token = Token.objects.create(user=self.owner)

        # Andere User
        self.other = User.objects.create_user("other", "other@example.com", "pass1234")
        create_profile_with_type(self.other, "business")
        self.other_token = Token.objects.create(user=self.other)

        # Angebot
        self.offer = Offer.objects.create(owner=self.owner, title="Delete Me", description="desc")
        self.url = reverse("offer-detail", args=[self.offer.id])

    def auth(self, token):
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

    def test_delete_success_204(self):
        self.auth(self.owner_token)
        res = self.client.delete(self.url)
        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Offer.objects.filter(id=self.offer.id).exists())

    def test_unauthenticated_returns_401(self):
        res = self.client.delete(self.url)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_forbidden_403_if_not_owner(self):
        self.auth(self.other_token)
        res = self.client.delete(self.url)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_not_found_404(self):
        self.auth(self.owner_token)
        bad_url = reverse("offer-detail", args=[999999])
        res = self.client.delete(bad_url)
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)
