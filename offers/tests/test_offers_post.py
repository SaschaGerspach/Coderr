# offers/tests/test_offers_post.py
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.db import models
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from profiles.models import Profile
from offers.models import Offer, OfferDetail


User = get_user_model()


def make_details_payload():
    return [
        {
            "title": "Basic Design",
            "revisions": 2,
            "delivery_time_in_days": 5,
            "price": "100.00",
            "features": ["Logo Design", "Visitenkarte"],
            "offer_type": "basic",
        },
        {
            "title": "Standard Design",
            "revisions": 5,
            "delivery_time_in_days": 7,
            "price": "200.00",
            "features": ["Logo Design", "Visitenkarte", "Briefpapier"],
            "offer_type": "standard",
        },
        {
            "title": "Premium Design",
            "revisions": 10,
            "delivery_time_in_days": 10,
            "price": "500.00",
            "features": ["Logo Design", "Visitenkarte", "Briefpapier", "Flyer"],
            "offer_type": "premium",
        },
    ]


def create_profile_with_type(user, target: str):
    """
    target: 'business' oder 'customer'
    Setzt den Profiltyp robust, egal wie das Feld im Profile-Modell heißt.
    Unterstützt:
      - CharField mit Choices, die 'business' und/oder 'customer' erlauben
      - Übliche textuelle Feldnamen: profile_type, type, user_type, account_type, role, kind, category
      - Bool-Felder: is_business, business, is_vendor (nur für 'business')
    """
    p = Profile.objects.create(user=user)

    # 1) CharField mit Choices
    for f in p._meta.fields:
        if isinstance(f, models.CharField) and getattr(f, "choices", None):
            allowed = {c[0] for c in f.choices}
            if target in allowed:
                setattr(p, f.name, target)
                p.save(update_fields=[f.name])
                return p

    # 2) Übliche textuelle Feldnamen
    for name in ["profile_type", "type", "user_type", "account_type", "role", "kind", "category"]:
        if hasattr(p, name):
            setattr(p, name, target)
            p.save(update_fields=[name])
            return p

    # 3) Bool-Varianten für business
    if target == "business":
        for name in ["is_business", "business", "is_vendor"]:
            if hasattr(p, name):
                setattr(p, name, True)
                p.save(update_fields=[name])
                return p

    # Wenn nichts passt, Tests bewusst fehlschlagen lassen, damit wir das tatsächliche Feld sehen
    raise AssertionError("Konnte kein geeignetes Profil-Feld für die Typ-Zuordnung finden")


class OfferCreateTests(APITestCase):
    def setUp(self):
        self.url = reverse("offer-create")

        # Business user
        self.biz_user = User.objects.create_user(
            username="biz", email="biz@example.com", password="pass1234"
        )
        create_profile_with_type(self.biz_user, "business")
        self.biz_token = Token.objects.create(user=self.biz_user)

        # Customer user
        self.cust_user = User.objects.create_user(
            username="cust", email="cust@example.com", password="pass1234"
        )
        create_profile_with_type(self.cust_user, "customer")
        self.cust_token = Token.objects.create(user=self.cust_user)

    def auth(self, token):
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

    def test_create_offer_success_business_user(self):
        self.auth(self.biz_token)
        payload = {
            "title": "Grafikdesign-Paket",
            "image": None,
            "description": "Ein umfassendes Grafikdesign-Paket für Unternehmen.",
            "details": make_details_payload(),
        }
        res = self.client.post(self.url, payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        # Response-Form prüfen
        self.assertIn("id", res.data)
        self.assertEqual(res.data["title"], payload["title"])
        self.assertIsNone(res.data["image"])
        self.assertEqual(res.data["description"], payload["description"])
        self.assertIn("details", res.data)
        self.assertEqual(len(res.data["details"]), 3)
        for item in res.data["details"]:
            self.assertIn("id", item)
            self.assertIn(item["offer_type"], ["basic", "standard", "premium"])

        # Datenbank angelegt
        self.assertEqual(Offer.objects.count(), 1)
        self.assertEqual(OfferDetail.objects.count(), 3)
        offer = Offer.objects.first()
        self.assertEqual(offer.owner, self.biz_user)

    def test_unauthenticated_returns_401(self):
        payload = {
            "title": "Grafikdesign-Paket",
            "image": None,
            "description": "Ein umfassendes Grafikdesign-Paket für Unternehmen.",
            "details": make_details_payload(),
        }
        res = self.client.post(self.url, payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_customer_user_forbidden_403(self):
        self.auth(self.cust_token)
        res = self.client.post(
            self.url,
            {
                "title": "Grafikdesign-Paket",
                "image": None,
                "description": "Ein umfassendes Grafikdesign-Paket für Unternehmen.",
                "details": make_details_payload(),
            },
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_invalid_details_count_returns_400(self):
        self.auth(self.biz_token)
        bad_details = make_details_payload()[:2]  # nur 2 statt 3
        res = self.client.post(
            self.url,
            {
                "title": "Grafikdesign-Paket",
                "image": None,
                "description": "desc",
                "details": bad_details,
            },
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("details", res.data)

    def test_duplicate_offer_type_returns_400(self):
        self.auth(self.biz_token)
        details = make_details_payload()
        details[1]["offer_type"] = "basic"  # doppelt
        res = self.client.post(
            self.url,
            {
                "title": "Grafikdesign-Paket",
                "image": None,
                "description": "desc",
                "details": details,
            },
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("details", res.data)

    def test_negative_price_returns_400(self):
        self.auth(self.biz_token)
        details = make_details_payload()
        details[0]["price"] = "-1.00"
        res = self.client.post(
            self.url,
            {
                "title": "Grafikdesign-Paket",
                "image": None,
                "description": "desc",
                "details": details,
            },
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_delivery_time_min_1_and_revisions_min_0(self):
        self.auth(self.biz_token)
        details = make_details_payload()
        details[0]["delivery_time_in_days"] = 0
        details[1]["revisions"] = -1
        res = self.client.post(
            self.url,
            {
                "title": "Grafikdesign-Paket",
                "image": None,
                "description": "desc",
                "details": details,
            },
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
