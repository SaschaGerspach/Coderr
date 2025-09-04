from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase, APIClient
from rest_framework.authtoken.models import Token
from profiles.models import Profile

User = get_user_model()

class CustomerProfileListTests(APITestCase):
    def setUp(self):
        # Customer-User (soll in der Liste erscheinen)
        self.user_customer = User.objects.create_user(
            username="cust", email="cust@mail.de", password="Pass123!"
        )
        self.profile_customer = Profile.objects.create(
            user=self.user_customer,
            type="customer",
            file="profile_picture_customer.jpg",
            # andere Felder dürfen fehlen; Serializer liefert dann "" statt None
        )

        # Business-User (darf NICHT in der Liste erscheinen)
        self.user_business = User.objects.create_user(
            username="biz", email="biz@mail.de", password="Pass123!"
        )
        self.profile_business = Profile.objects.create(user=self.user_business, type="business")

        # Auth-Client
        self.client_auth = APIClient()
        self.client_auth.credentials(
            HTTP_AUTHORIZATION="Token " + Token.objects.create(user=self.user_customer).key
        )

        self.client_anon = APIClient()
        self.url = reverse("customer-profiles")

    def test_authenticated_user_gets_customer_profiles_only(self):
        resp = self.client_auth.get(self.url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        # nur 1 Eintrag (der Customer)
        self.assertEqual(len(resp.data), 1)
        item = resp.data[0]
        self.assertEqual(item["user"], self.user_customer.id)
        self.assertEqual(item["username"], "cust")
        self.assertEqual(item["type"], "customer")
        # Business darf nicht drin sein
        ids = [p["user"] for p in resp.data]
        self.assertNotIn(self.user_business.id, ids)

    def test_response_shape_matches_spec(self):
        resp = self.client_auth.get(self.url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        item = resp.data[0]

        # Felder laut Spez vorhanden …
        expected_fields = {"user", "username", "first_name", "last_name", "file", "uploaded_at", "type"}
        for f in expected_fields:
            self.assertIn(f, item, f"Feld {f} fehlt in der Response")

        # … und bestimmte Felder dürfen NICHT enthalten sein
        for f in ["email", "created_at", "location", "tel", "description", "working_hours"]:
            self.assertNotIn(f, item, f"Feld {f} sollte NICHT in der Response sein")

        # Nie null (gemäß deiner Serializer-Logik) – leere Strings sind ok
        for f in ["first_name", "last_name", "type"]:
            self.assertIsNotNone(item[f], f"{f} sollte nicht None sein")

        # Optional: Datei übernommen?
        self.assertEqual(item["file"], "profile_picture_customer.jpg")

        # uploaded_at im ISO-Format ohne Mikrosekunden (global über SETTINGS geregelt)
        self.assertIsInstance(item["uploaded_at"], str)
        self.assertTrue(item["uploaded_at"])

    def test_unauthenticated_gets_401(self):
        resp = self.client_anon.get(self.url)
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)
