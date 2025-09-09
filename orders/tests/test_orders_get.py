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


class OrderListTests(APITestCase):
    def setUp(self):
        self.url = reverse("order-create")  # gleiche URL für GET und POST

        # Beteiligte Nutzer
        self.biz = User.objects.create_user("biz", "biz@example.com", "pass1234")
        create_profile_with_type(self.biz, "business")
        self.biz_token = Token.objects.create(user=self.biz)

        self.cust = User.objects.create_user("cust", "cust@example.com", "pass1234")
        create_profile_with_type(self.cust, "customer")
        self.cust_token = Token.objects.create(user=self.cust)

        # Anderer Nutzer (nicht beteiligt)
        self.other = User.objects.create_user("other", "other@example.com", "pass1234")
        create_profile_with_type(self.other, "customer")
        self.other_token = Token.objects.create(user=self.other)

        # Angebot des Business + Details
        offer, detail = add_offer_with_detail(self.biz)

        # Zwei Orders: eine, wo cust Kunde ist; eine, wo biz Kunde ist (damit beide Richtungen abgedeckt sind)
        self.order1 = Order.objects.create(
            customer_user=self.cust,
            business_user=self.biz,
            offer_detail=detail,
            title=detail.title,
            revisions=detail.revisions,
            delivery_time_in_days=detail.delivery_time_in_days,
            price=detail.price,
            features=detail.features,
            offer_type=detail.offer_type,
            status=Order.Status.IN_PROGRESS,
        )
        self.order2 = Order.objects.create(
            customer_user=self.biz,      # biz als Kunde
            business_user=self.cust,     # cust als Business (konstruiert, aber ok für Filter-Test)
            offer_detail=detail,
            title=detail.title,
            revisions=detail.revisions,
            delivery_time_in_days=detail.delivery_time_in_days,
            price=detail.price,
            features=detail.features,
            offer_type=detail.offer_type,
            status=Order.Status.IN_PROGRESS,
        )
        # Fremde Order, an der keiner von (cust/biz) beteiligt ist:
        o_user = self.other
        offer2, detail2 = add_offer_with_detail(o_user, title="X", detail_title="Y", price="10.00")
        self.unrelated = Order.objects.create(
            customer_user=o_user,
            business_user=o_user,
            offer_detail=detail2,
            title=detail2.title,
            revisions=detail2.revisions,
            delivery_time_in_days=detail2.delivery_time_in_days,
            price=detail2.price,
            features=detail2.features,
            offer_type=detail2.offer_type,
            status=Order.Status.IN_PROGRESS,
        )

    def auth(self, token):
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

    def test_list_requires_auth_401(self):
        res = self.client.get(self.url)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_list_returns_orders_where_user_is_customer_or_business(self):
        # als cust eingeloggt → order1 (cust= kundenseitig), order2 (business-seitig) sind relevant
        self.auth(self.cust_token)
        res = self.client.get(self.url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIsInstance(res.data, list)
        ids = {o["id"] for o in res.data}
        self.assertIn(self.order1.id, ids)
        self.assertIn(self.order2.id, ids)
        self.assertNotIn(self.unrelated.id, ids)

    def test_list_as_business(self):
        # als biz eingeloggt → order1 (businessseitig), order2 (kundenseitig) sind relevant
        self.auth(self.biz_token)
        res = self.client.get(self.url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        ids = {o["id"] for o in res.data}
        self.assertIn(self.order1.id, ids)
        self.assertIn(self.order2.id, ids)
        self.assertNotIn(self.unrelated.id, ids)
