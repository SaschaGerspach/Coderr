from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase, APIClient
from profiles.models import Profile

User = get_user_model()

class RegistrationTests(APITestCase):
    def setUp(self):
        self.url = reverse("registration")
        self.client = APIClient()

    def test_registration_success(self):
        payload = {
            "username": "exampleUsername",
            "email": "example@mail.de",
            "password": "StrongPassw0rd!",
            "repeated_password": "StrongPassw0rd!",
            "type": "customer",
        }
        resp = self.client.post(self.url, payload, format="json")
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertIn("token", resp.data)
        self.assertIn("user_id", resp.data)
        self.assertEqual(resp.data["username"], payload["username"])
        self.assertEqual(resp.data["email"], payload["email"])
        self.assertTrue(User.objects.filter(username=payload["username"]).exists())

    def test_password_mismatch_400(self):
        payload = {
            "username": "u2",
            "email": "u2@mail.de",
            "password": "StrongPassw0rd!",
            "repeated_password": "DIFFERENT123!",
            "type": "customer",
        }
        resp = self.client.post(self.url, payload, format="json")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("repeated_password", resp.data)

    def test_duplicate_username_400(self):
        User.objects.create_user(username="taken", email="t@mail.de", password="abc12345")
        payload = {
            "username": "taken",
            "email": "new@mail.de",
            "password": "StrongPassw0rd!",
            "repeated_password": "StrongPassw0rd!",
            "type": "business",
        }
        resp = self.client.post(self.url, payload, format="json")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("username", resp.data)

    def test_duplicate_email_400(self):
        User.objects.create_user(username="u1", email="dup@mail.de", password="abc12345")
        payload = {
            "username": "u2",
            "email": "dup@mail.de",
            "password": "StrongPassw0rd!",
            "repeated_password": "StrongPassw0rd!",
            "type": "customer",
        }
        resp = self.client.post(self.url, payload, format="json")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("email", resp.data)

    def test_missing_required_fields_400(self):
        resp = self.client.post(self.url, {"username": "x"}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        for f in ("email", "password", "repeated_password", "type"):
            self.assertIn(f, resp.data)

    def test_registration_creates_profile_with_type(self):
        payload = {
            "username": "reg_user",
            "email": "reg@mail.de",
            "password": "StrongPassw0rd!",
            "repeated_password": "StrongPassw0rd!",
            "type": "business",
        }
        resp = self.client.post(self.url, payload, format="json")
        self.assertEqual(resp.status_code, 201)
        user_id = resp.data["user_id"]

        # Profil existiert und hat den Type übernommen
        prof = Profile.objects.get(user_id=user_id)
        self.assertEqual(prof.type, "business")