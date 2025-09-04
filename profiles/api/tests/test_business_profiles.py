from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase, APIClient
from rest_framework.authtoken.models import Token
from profiles.models import Profile

User = get_user_model()

class BusinessProfileListTests(APITestCase):
    def setUp(self):
        # Business-User
        self.user_business = User.objects.create_user(
            username="biz", email="biz@mail.de", password="Pass123!"
        )
        self.profile_business = Profile.objects.create(
            user=self.user_business,
            type="business",
            location="Berlin",
            tel="123456789",
            description="Business description",
            working_hours="9-17",
            file="profile_picture.jpg",
        )

        # Customer-User
        self.user_customer = User.objects.create_user(
            username="cust", email="cust@mail.de", password="Pass123!"
        )
        self.profile_customer = Profile.objects.create(user=self.user_customer, type="customer")

        # Clients
        self.client_auth = APIClient()
        self.client_auth.credentials(HTTP_AUTHORIZATION="Token " + Token.objects.create(user=self.user_business).key)
        self.client_anon = APIClient()

        self.url = reverse("business-profiles")

    def test_authenticated_user_gets_business_profiles(self):
        resp = self.client_auth.get(self.url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data), 1)
        self.assertEqual(resp.data[0]["type"], "business")
        self.assertEqual(resp.data[0]["username"], "biz")

    def test_no_customer_profiles_in_list(self):
        resp = self.client_auth.get(self.url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        for profile in resp.data:
            self.assertEqual(profile["type"], "business")

    def test_unauthenticated_gets_401(self):
        resp = self.client_anon.get(self.url)
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)
