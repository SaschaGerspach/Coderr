from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from profiles.models import Profile
from offers.models import Offer, OfferDetail


User = get_user_model()


def create_profile_with_type(user, target: str):
    # Dein Profile hat .type (Choices customer/business)
    p = Profile.objects.create(user=user)
    p.type = target
    p.save(update_fields=["type"])
    return p


def add_offer_with_details(owner):
    offer = Offer.objects.create(owner=owner, title="Logo Design", description="desc")
    # Drei Details
    basic = OfferDetail.objects.create(
        offer=offer,
        title="Basic",
        revisions=3,
        delivery_time_in_days=5,
        price="150.00",
        features=["Logo Design", "Visitenkarten"],
        offer_type="basic",
    )
    standard = OfferDetail.objects.create(
        offer=offer,
        title="Standard",
        revisions=5,
        delivery_time_in_days=7,
        price="300.00",
        features=["Logo Design", "Briefpapier"],
        offer_type="standard",
    )
    premium = OfferDetail.objects.create(
        offer=offer,
        title="Premium",
        revisions=8,
        delivery_time_in_days=10,
        price="600.00",
        features=["Alles"],
        offer_type="premium",
    )
    return offer, basic, standard, premium


class OrderCreateTests(APITestCase):
    def setUp(self):
        self.url = reverse("order-create")

        # Business-Anbieter
        self.biz = User.objects.create_user("biz", "biz@example.com", "pass1234")
        create_profile_with_type(self.biz, "business")
        self.biz_token = Token.objects.create(user=self.biz)

        # Customer-Kunde
        self.cust = User.objects.create_user("cust", "cust@example.com", "pass1234")
        create_profile_with_type(self.cust, "customer")
        self.cust_token = Token.objects.create(user=self.cust)

        # Angebot + Details des Business
        self.offer, self.basic, self.standard, self.premium = add_offer_with_details(self.biz)

    def auth(self, token):
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

    def test_create_order_success_201(self):
        self.auth(self.cust_token)
        payload = {"offer_detail_id": self.basic.id}
        res = self.client.post(self.url, payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        data = res.data
        self.assertIn("id", data)
        self.assertEqual(data["customer_user"], self.cust.id)
        self.assertEqual(data["business_user"], self.biz.id)
        self.assertEqual(data["title"], "Basic")
        self.assertEqual(data["revisions"], 3)
        self.assertEqual(data["delivery_time_in_days"], 5)
        self.assertEqual(float(data["price"]), 150.0)
        self.assertEqual(data["features"], ["Logo Design", "Visitenkarten"])
        self.assertEqual(data["offer_type"], "basic")
        self.assertEqual(data["status"], "in_progress")
        self.assertIn("created_at", data)
        self.assertIn("updated_at", data)

    def test_unauthenticated_returns_401(self):
        res = self.client.post(self.url, {"offer_detail_id": self.basic.id}, format="json")
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_forbidden_if_not_customer_403(self):
        # Business versucht zu bestellen
        self.auth(self.biz_token)
        res = self.client.post(self.url, {"offer_detail_id": self.basic.id}, format="json")
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_own_offer_forbidden_403(self):
        # Ein Customer besitzt ein eigenes Offer und versucht, es zu bestellen -> 403
        other_cust = User.objects.create_user("cust2", "cust2@example.com", "pass1234")
        create_profile_with_type(other_cust, "customer")
        other_cust_token = Token.objects.create(user=other_cust)

        offer = Offer.objects.create(owner=other_cust, title="Tmp", description="tmp")
        od = OfferDetail.objects.create(
            offer=offer,
            title="TmpBasic",
            revisions=1,
            delivery_time_in_days=2,
            price="10.00",
            features=["x"],
            offer_type="basic",
        )

        # <-- Fix: hier korrekt das Token übergeben
        self.auth(other_cust_token)
        res = self.client.post(self.url, {"offer_detail_id": od.id}, format="json")
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_missing_offer_detail_id_returns_400(self):
        self.auth(self.cust_token)
        res = self.client.post(self.url, {}, format="json")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_invalid_offer_detail_returns_404_or_400(self):
        self.auth(self.cust_token)
        res = self.client.post(self.url, {"offer_detail_id": 999999}, format="json")
        # Je nach deiner View-Mapping-Variante akzeptieren wir 404 (bevorzugt) oder 400.
        self.assertIn(res.status_code, (status.HTTP_404_NOT_FOUND, status.HTTP_400_BAD_REQUEST))
