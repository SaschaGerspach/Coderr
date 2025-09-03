from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase, APIClient

User = get_user_model()

class LoginTests(APITestCase):
    def setUp(self):
        self.url = reverse("login")
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="exampleUsername",
            email="example@mail.de",
            password="examplePassword"
        )

    def test_login_success(self):
        payload = {
            "username": "exampleUsername",
            "password": "examplePassword"
        }
        resp = self.client.post(self.url, payload, format="json")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn("token", resp.data)
        self.assertEqual(resp.data["username"], "exampleUsername")
        self.assertEqual(resp.data["email"], "example@mail.de")
        self.assertEqual(resp.data["user_id"], self.user.id)

    def test_login_wrong_password(self):
        payload = {
            "username": "exampleUsername",
            "password": "wrongPassword"
        }
        resp = self.client.post(self.url, payload, format="json")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("detail", resp.data)

    def test_login_unknown_user(self):
        payload = {
            "username": "doesnotexist",
            "password": "whatever123"
        }
        resp = self.client.post(self.url, payload, format="json")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("detail", resp.data)

    def test_login_missing_fields(self):
        resp = self.client.post(self.url, {"username": "exampleUsername"}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("password", resp.data)
