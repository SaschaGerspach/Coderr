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
    # 1) CharField mit Choices
    for f in p._meta.fields:
        if isinstance(f, models.CharField) and getattr(f, "choices", None):
            allowed = {c[0] for c in f.choices}
            if target in allowed:
                setattr(p, f.name, target)
                p.save(update_fields=[f.name])
                return p
    # 2) Textfeld-Alternativen
    for name in ["profile_type", "type", "user_type", "account_type", "role", "kind", "category"]:
        if hasattr(p, name):
            setattr(p, name, target)
            p.save(update_fields=[name])
            return p
    # 3) Bool für business
    if target == "business":
        for name in ["is_business", "business", "is_vendor"]:
            if hasattr(p, name):
                setattr(p, name, True)
                p.save(update_fields=[name])
                return p
    raise AssertionError("Kein passendes Profil-Feld gefunden")


def add_offer(user):
    offer = Offer.objects.create(owner=user, title="Grafikdesign-Paket", description="Ein umfassendes Paket.")
    OfferDetail.objects.create(
        offer=offer, title="Basic Design", revisions=2, delivery_time_in_days=5,
        price="100.00", features=["Logo Design", "Visitenkarte"], offer_type="basic"
    )
    OfferDetail.objects.create(
        offer=offer, title="Standard Design", revisions=5, delivery_time_in_days=10,
        price="120.00", features=["Logo Design", "Visitenkarte", "Briefpapier"], offer_type="standard"
    )
    OfferDetail.objects.create(
        offer=offer, title="Premium Design", revisions=10, delivery_time_in_days=10,
        price="150.00", features=["Logo Design", "Visitenkarte", "Briefpapier", "Flyer"], offer_type="premium"
    )
    return offer


class OfferPatchTests(APITestCase):
    def setUp(self):
        # Owner
        self.owner = User.objects.create_user("owner", "owner@example.com", "pass1234")
        create_profile_with_type(self.owner, "business")
        self.owner_token = Token.objects.create(user=self.owner)

        # Andere User (kein Owner)
        self.other = User.objects.create_user("other", "other@example.com", "pass1234")
        create_profile_with_type(self.other, "business")
        self.other_token = Token.objects.create(user=self.other)

        # Angebot + Details
        self.offer = add_offer(self.owner)
        self.url = reverse("offer-detail", args=[self.offer.id])

        # IDs merken
        self.detail_basic = self.offer.details.get(offer_type="basic")
        self.detail_standard = self.offer.details.get(offer_type="standard")
        self.detail_premium = self.offer.details.get(offer_type="premium")

    def auth(self, token):
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

    def test_patch_success_update_title_and_one_detail(self):
        self.auth(self.owner_token)
        payload = {
            "title": "Updated Grafikdesign-Paket",
            "details": [
                {
                    "offer_type": "basic",
                    "title": "Basic Design Updated",
                    "revisions": 3,
                    "delivery_time_in_days": 6,
                    "price": 120,
                    "features": ["Logo Design", "Flyer"]
                }
            ]
        }
        res = self.client.patch(self.url, payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        # volle Representation (OfferSerializer)
        self.assertEqual(res.data["title"], "Updated Grafikdesign-Paket")
        self.assertEqual(len(res.data["details"]), 3)

        # IDs bleiben erhalten
        updated_basic = next(d for d in res.data["details"] if d["offer_type"] == "basic")
        self.assertEqual(updated_basic["id"], self.detail_basic.id)
        self.assertEqual(updated_basic["title"], "Basic Design Updated")
        self.assertEqual(updated_basic["revisions"], 3)
        self.assertEqual(updated_basic["delivery_time_in_days"], 6)
        self.assertEqual(float(updated_basic["price"]), 120.0)
        self.assertEqual(updated_basic["features"], ["Logo Design", "Flyer"])

        # andere Details unverändert
        std = next(d for d in res.data["details"] if d["offer_type"] == "standard")
        self.assertEqual(std["id"], self.detail_standard.id)
        prem = next(d for d in res.data["details"] if d["offer_type"] == "premium")
        self.assertEqual(prem["id"], self.detail_premium.id)

    def test_unauthenticated_401(self):
        res = self.client.patch(self.url, {"title": "X"}, format="json")
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_forbidden_403_if_not_owner(self):
        self.auth(self.other_token)
        res = self.client.patch(self.url, {"title": "X"}, format="json")
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_not_found_404(self):
        self.auth(self.owner_token)
        bad = reverse("offer-detail", args=[999999])
        res = self.client.patch(bad, {"title": "X"}, format="json")
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)

    def test_details_requires_offer_type_and_existing_detail(self):
        self.auth(self.owner_token)
        # missing offer_type
        res1 = self.client.patch(self.url, {"details": [{"title": "x"}]}, format="json")
        self.assertEqual(res1.status_code, status.HTTP_400_BAD_REQUEST)

        # non existing offer_type for this offer
        res2 = self.client.patch(self.url, {"details": [{"offer_type": "basic", "id": self.detail_standard.id}]}, format="json")
        self.assertEqual(res2.status_code, status.HTTP_400_BAD_REQUEST)

    def test_invalid_values_return_400(self):
        self.auth(self.owner_token)
        # negative price, delivery_time 0
        payload = {
            "details": [
                {"offer_type": "basic", "price": -1},
                {"offer_type": "standard", "delivery_time_in_days": 0},
            ]
        }
        res = self.client.patch(self.url, payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
