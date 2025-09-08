# offers/tests/test_offers_get.py
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.db import models
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

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
    # 2) Übliche Namen
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


def add_offer(user, title="Website Design", desc="Professionelles Website-Design..."):
    offer = Offer.objects.create(owner=user, title=title, image=None, description=desc)
    OfferDetail.objects.create(
        offer=offer, title="Basic", revisions=1, delivery_time_in_days=7, price="100.00",
        features=["x"], offer_type="basic"
    )
    OfferDetail.objects.create(
        offer=offer, title="Standard", revisions=2, delivery_time_in_days=5, price="150.00",
        features=["x"], offer_type="standard"
    )
    OfferDetail.objects.create(
        offer=offer, title="Premium", revisions=3, delivery_time_in_days=10, price="500.00",
        features=["x"], offer_type="premium"
    )
    return offer


class OfferListTests(APITestCase):
    def setUp(self):
        self.url = reverse("offer-create")  # gleiche Route
        self.user_a = User.objects.create_user("a", "a@example.com", "pass1234")
        create_profile_with_type(self.user_a, "business")

        self.user_b = User.objects.create_user("b", "b@example.com", "pass1234")
        create_profile_with_type(self.user_b, "business")

        self.offer_a = add_offer(self.user_a, title="Website Design A", desc="Professionelles Website-Design A")
        self.offer_b = add_offer(self.user_b, title="Logo Paket", desc="Logo Erstellung und Branding")

    def test_list_offers_200_no_auth_required(self):
        res = self.client.get(self.url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("results", res.data)
        self.assertGreaterEqual(res.data["count"], 2)
        first = res.data["results"][0]
        self.assertIn("id", first)
        self.assertIn("user", first)
        self.assertIn("details", first)
        self.assertIn("min_price", first)
        self.assertIn("min_delivery_time", first)
        self.assertIn("user_details", first)

    def test_filter_by_creator_id(self):
        res = self.client.get(self.url, {"creator_id": self.user_a.id})
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        for item in res.data["results"]:
            self.assertEqual(item["user"], self.user_a.id)

    def test_filter_by_min_price(self):
        # min_price 120 sollte Angebot mit min_price 100 ausschließen, min bleibt 150 (weil kleinster Preis 100 < 120)
        res = self.client.get(self.url, {"min_price": "120"})
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        # Sicherstellen, dass nur Offres mit _min_price >= 120 zurückkommen
        for item in res.data["results"]:
            self.assertGreaterEqual(float(item["min_price"]), 120.0)

    def test_filter_by_max_delivery_time(self):
        # max_delivery_time 6 erlaubt nur Angebote mit minimaler Lieferzeit <= 6 (bei offer_a ist min 5)
        res = self.client.get(self.url, {"max_delivery_time": "6"})
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        for item in res.data["results"]:
            self.assertLessEqual(int(item["min_delivery_time"]), 6)

    def test_search_in_title_description(self):
        res = self.client.get(self.url, {"search": "Logo"})
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        # alle Ergebnisse sollen 'Logo' im title oder description enthalten
        for item in res.data["results"]:
            text = (item["title"] or "") + " " + (item["description"] or "")
            self.assertIn("logo".lower(), text.lower())

    def test_ordering_by_min_price(self):
        res = self.client.get(self.url, {"ordering": "min_price"})
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        prices = [float(x["min_price"]) for x in res.data["results"]]
        self.assertEqual(prices, sorted(prices))

        res_desc = self.client.get(self.url, {"ordering": "-min_price"})
        self.assertEqual(res_desc.status_code, status.HTTP_200_OK)
        prices_desc = [float(x["min_price"]) for x in res_desc.data["results"]]
        self.assertEqual(prices_desc, sorted(prices_desc, reverse=True))

    def test_invalid_params_return_400(self):
        r1 = self.client.get(self.url, {"creator_id": "abc"})
        r2 = self.client.get(self.url, {"min_price": "oops"})
        r3 = self.client.get(self.url, {"max_delivery_time": "x"})
        r4 = self.client.get(self.url, {"ordering": "title"})  # nicht erlaubt
        self.assertEqual(r1.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(r2.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(r3.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(r4.status_code, status.HTTP_400_BAD_REQUEST)

    def test_pagination_with_page_size(self):
        res = self.client.get(self.url, {"page_size": 1})
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data["results"]), 1)
        self.assertIn("next", res.data)
