from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from profiles.models import Profile
from reviews.models import Review

User = get_user_model()

def make_user(username, ptype):
    u = User.objects.create_user(username, f"{username}@ex.com", "pass1234")
    Profile.objects.create(user=u, type=ptype)
    tok = Token.objects.create(user=u)
    return u, tok

class ReviewPatchTests(APITestCase):
    def setUp(self):
        # Business (Ziel der Review)
        self.biz, _ = make_user("biz1", "business")
        # Owner/Reviewer
        self.owner, self.owner_tok = make_user("cust1", "customer")
        # Anderer eingeloggter User
        self.other, self.other_tok = make_user("cust2", "customer")

        self.review = Review.objects.create(
            business_user=self.biz,
            reviewer=self.owner,
            rating=3,
            description="ok",
        )
        self.url = reverse("review-detail", args=[self.review.id])

    def auth(self, tok):
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {tok.key}")

    def test_owner_can_patch_rating_and_description(self):
        self.auth(self.owner_tok)
        res = self.client.patch(self.url, {"rating": 5, "description": "Noch besser als erwartet!"}, format="json")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["id"], self.review.id)
        self.assertEqual(res.data["rating"], 5)
        self.assertEqual(res.data["description"], "Noch besser als erwartet!")
        # unveränderte Felder vorhanden
        for key in ["business_user", "reviewer", "created_at", "updated_at"]:
            self.assertIn(key, res.data)

    def test_requires_auth_401(self):
        res = self.client.patch(self.url, {"rating": 4}, format="json")
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_forbidden_if_not_owner_403(self):
        self.auth(self.other_tok)
        res = self.client.patch(self.url, {"rating": 4}, format="json")
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_invalid_rating_400(self):
        self.auth(self.owner_tok)
        res = self.client.patch(self.url, {"rating": 0}, format="json")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        res = self.client.patch(self.url, {"rating": 6}, format="json")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_extra_fields_cause_400(self):
        self.auth(self.owner_tok)
        res = self.client.patch(self.url, {"rating": 5, "business_user": 999}, format="json")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_not_found_404(self):
        self.auth(self.owner_tok)
        bad = reverse("review-detail", args=[999999])
        res = self.client.patch(bad, {"rating": 4}, format="json")
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)
