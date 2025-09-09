from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from profiles.models import Profile
from offers.models import Offer, OfferDetail
from orders.models import Order

User = get_user_model()

def create_profile_with_type(user, t: str):
    p = Profile.objects.create(user=user)
    p.type = t
    p.save(update_fields=["type"])
    return p

def add_offer_with_detail(owner, title="Logo Design", detail_title="Basic", price="150.00"):
    offer = Offer.objects.create(owner=owner, title=title, description="desc")
    detail = OfferDetail.objects.create(
        offer=offer,
        title=detail_title,
        revisions=3,
        delivery_time_in_days=5,
        price=price,
        features=["Logo Design", "Visitenkarten"],
        offer_type="basic",
    )
    return offer, detail

def create_order(customer, business, detail):
    return Order.objects.create(
        customer_user=customer,
        business_user=business,
        offer_detail=detail,
        title=detail.title,
        revisions=detail.revisions,
        delivery_time_in_days=detail.delivery_time_in_days,
        price=detail.price,
        features=detail.features,
        offer_type=detail.offer_type,
        status=Order.Status.IN_PROGRESS,
    )

class OrderPatchTests(APITestCase):
    def setUp(self):
        # Nutzer
        self.biz = User.objects.create_user("biz", "biz@example.com", "pass1234")
        create_profile_with_type(self.biz, "business")
        self.biz_token = Token.objects.create(user=self.biz)

        self.cust = User.objects.create_user("cust", "cust@example.com", "pass1234")
        create_profile_with_type(self.cust, "customer")
        self.cust_token = Token.objects.create(user=self.cust)

        self.other_biz = User.objects.create_user("obiz", "obiz@example.com", "pass1234")
        create_profile_with_type(self.other_biz, "business")
        self.other_biz_token = Token.objects.create(user=self.other_biz)

        # Offer & Detail (gehört biz)
        _, self.detail = add_offer_with_detail(self.biz)

        # Order: cust ↔ biz
        self.order = create_order(customer=self.cust, business=self.biz, detail=self.detail)
        self.url = reverse("order-detail", args=[self.order.id])

    def auth(self, token):
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

    def test_patch_status_success_by_business(self):
        self.auth(self.biz_token)
        res = self.client.patch(self.url, {"status": "completed"}, format="json")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["id"], self.order.id)
        self.assertEqual(res.data["status"], "completed")
        # volle Repräsentation vorhanden:
        for key in ["customer_user","business_user","title","revisions","delivery_time_in_days","price","features","offer_type","created_at","updated_at"]:
            self.assertIn(key, res.data)

    def test_unauthenticated_401(self):
        res = self.client.patch(self.url, {"status": "completed"}, format="json")
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_forbidden_if_customer_403(self):
        self.auth(self.cust_token)
        res = self.client.patch(self.url, {"status": "completed"}, format="json")
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_forbidden_if_other_business_not_participant_403(self):
        self.auth(self.other_biz_token)
        res = self.client.patch(self.url, {"status": "completed"}, format="json")
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_invalid_status_400(self):
        self.auth(self.biz_token)
        res = self.client.patch(self.url, {"status": "foobar"}, format="json")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_extra_fields_cause_400(self):
        self.auth(self.biz_token)
        res = self.client.patch(self.url, {"status": "completed", "title": "hax"}, format="json")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_not_found_404(self):
        self.auth(self.biz_token)
        bad = reverse("order-detail", args=[999999])
        res = self.client.patch(bad, {"status": "completed"}, format="json")
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)
