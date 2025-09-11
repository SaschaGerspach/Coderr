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


class ReviewDeleteTests(APITestCase):
    def setUp(self):
        # Business (Ziel)
        self.biz, _ = make_user("biz1", "business")
        # Owner/Reviewer
        self.owner, self.owner_tok = make_user("cust1", "customer")
        # Fremder User
        self.other, self.other_tok = make_user("cust2", "customer")

        self.review = Review.objects.create(
            business_user=self.biz,
            reviewer=self.owner,
            rating=4,
            description="nice",
        )
        self.url = reverse("review-detail", args=[self.review.id])

    def auth(self, tok):
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {tok.key}")

    def test_delete_success_by_owner_204(self):
        self.auth(self.owner_tok)
        res = self.client.delete(self.url)
        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Review.objects.filter(id=self.review.id).exists())

    def test_requires_auth_401(self):
        res = self.client.delete(self.url)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_forbidden_if_not_owner_403(self):
        self.auth(self.other_tok)
        res = self.client.delete(self.url)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_not_found_404(self):
        self.auth(self.owner_tok)
        bad = reverse("review-detail", args=[999999])
        res = self.client.delete(bad)
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)
