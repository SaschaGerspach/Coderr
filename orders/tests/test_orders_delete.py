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

def add_offer_with_detail(owner):
    offer = Offer.objects.create(owner=owner, title="X", description="desc")
    detail = OfferDetail.objects.create(
        offer=offer, title="Basic", revisions=1, delivery_time_in_days=3,
        price="50.00", features=["x"], offer_type="basic"
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

class OrderDeleteTests(APITestCase):
    def setUp(self):
        # Business
        self.biz = User.objects.create_user("biz", "biz@example.com", "pass1234")
        create_profile_with_type(self.biz, "business")
        self.biz_token = Token.objects.create(user=self.biz)

        # Customer
        self.cust = User.objects.create_user("cust", "cust@example.com", "pass1234")
        create_profile_with_type(self.cust, "customer")
        self.cust_token = Token.objects.create(user=self.cust)

        # Staff-Admin
        self.admin = User.objects.create_user("admin", "admin@example.com", "pass1234", is_staff=True)
        create_profile_with_type(self.admin, "customer")
        self.admin_token = Token.objects.create(user=self.admin)

        # Angebot & Order
        _, self.detail = add_offer_with_detail(self.biz)
        self.order = create_order(self.cust, self.biz, self.detail)
        self.url = reverse("order-detail", args=[self.order.id])  # gleiche URL wie PATCH

    def auth(self, token):
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

    def test_delete_success_by_admin(self):
        self.auth(self.admin_token)
        res = self.client.delete(self.url)
        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Order.objects.filter(id=self.order.id).exists())

    def test_delete_requires_auth_401(self):
        res = self.client.delete(self.url)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_delete_forbidden_for_non_admin_403(self):
        self.auth(self.cust_token)
        res = self.client.delete(self.url)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_delete_not_found_404(self):
        self.auth(self.admin_token)
        bad = reverse("order-detail", args=[99999])
        res = self.client.delete(bad)
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)
