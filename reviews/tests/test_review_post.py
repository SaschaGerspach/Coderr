from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from profiles.models import Profile

User = get_user_model()


def create_profile_with_type(user, t: str):
    p = Profile.objects.create(user=user)
    p.type = t
    p.save(update_fields=["type"])
    return p


class ReviewCreateTests(APITestCase):
    def setUp(self):
        self.url = reverse("review-create")

        # Business-User (Ziel)
        self.biz = User.objects.create_user("biz", "biz@example.com", "pass1234")
        create_profile_with_type(self.biz, "business")

        # Customer-Reviewer
        self.cust = User.objects.create_user("cust", "cust@example.com", "pass1234")
        create_profile_with_type(self.cust, "customer")
        self.cust_token = Token.objects.create(user=self.cust)

        # Business-Reviewer (verboten)
        self.biz2 = User.objects.create_user("biz2", "biz2@example.com", "pass1234")
        create_profile_with_type(self.biz2, "business")
        self.biz2_token = Token.objects.create(user=self.biz2)

        # Customer ohne Token-Auth use-case: handled by .auth()

    def auth(self, token):
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

    def test_create_review_success_201(self):
        self.auth(self.cust_token)
        payload = {"business_user": self.biz.id, "rating": 5, "description": "Hervorragende Erfahrung!"}
        res = self.client.post(self.url, payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertIn("id", res.data)
        self.assertEqual(res.data["business_user"], self.biz.id)
        self.assertEqual(res.data["reviewer"], self.cust.id)
        self.assertEqual(res.data["rating"], 5)
        self.assertEqual(res.data["description"], "Hervorragende Erfahrung!")
        self.assertIn("created_at", res.data)
        self.assertIn("updated_at", res.data)

    def test_unauthenticated_401(self):
        payload = {"business_user": self.biz.id, "rating": 4, "description": "ok"}
        res = self.client.post(self.url, payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_business_profile_cannot_review_403(self):
        self.auth(self.biz2_token)
        payload = {"business_user": self.biz.id, "rating": 4, "description": "nope"}
        res = self.client.post(self.url, payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_duplicate_review_returns_400(self):
        self.auth(self.cust_token)
        payload = {"business_user": self.biz.id, "rating": 4, "description": "nice"}
        res1 = self.client.post(self.url, payload, format="json")
        self.assertEqual(res1.status_code, status.HTTP_201_CREATED)

        res2 = self.client.post(self.url, payload, format="json")
        self.assertEqual(res2.status_code, status.HTTP_400_BAD_REQUEST)

    def test_invalid_rating_returns_400(self):
        self.auth(self.cust_token)
        payload = {"business_user": self.biz.id, "rating": 0, "description": "too low"}
        res = self.client.post(self.url, payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

        payload["rating"] = 6
        res = self.client.post(self.url, payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_non_business_target_returns_400(self):
        # Target ist kein Business
        nonbiz = User.objects.create_user("u", "u@example.com", "pass1234")
        create_profile_with_type(nonbiz, "customer")
        self.auth(self.cust_token)
        payload = {"business_user": nonbiz.id, "rating": 3, "description": "x"}
        res = self.client.post(self.url, payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_payload_reviewer_ignored_server_sets_reviewer(self):
        # Falls jemand versucht reviewer zu fälschen – wird ignoriert
        self.auth(self.cust_token)
        payload = {
            "business_user": self.biz.id,
            "rating": 5,
            "description": "x",
            "reviewer": 9999,  # sollte ignoriert werden
        }
        res = self.client.post(self.url, payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.data["reviewer"], self.cust.id)
