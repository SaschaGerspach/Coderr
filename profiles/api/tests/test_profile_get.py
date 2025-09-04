from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase, APIClient
from rest_framework.authtoken.models import Token
from profiles.models import Profile

User = get_user_model()

class ProfileGetTests(APITestCase):
    def setUp(self):
        # User A (business)
        self.user_a = User.objects.create_user(username="user_a", email="a@mail.de", password="Pass123!")
        self.profile_a = Profile.objects.create(
            user=self.user_a,
            type="business",
            location="Berlin",
            tel="123456789",
            description="Business description",
            working_hours="9-17",
            file="profile_picture.jpg",
        )
        # User B (customer)
        self.user_b = User.objects.create_user(username="user_b", email="b@mail.de", password="Pass123!")
        self.profile_b = Profile.objects.create(user=self.user_b, type="customer")

        # Auth-Clients
        self.client_a = APIClient()
        self.client_a.credentials(HTTP_AUTHORIZATION="Token " + Token.objects.create(user=self.user_a).key)

        self.client_b = APIClient()
        self.client_b.credentials(HTTP_AUTHORIZATION="Token " + Token.objects.create(user=self.user_b).key)

        self.anon = APIClient()

        # NEU: ein einheitlicher URL-Name
        self.url_detail_a = reverse("profile", kwargs={"pk": self.user_a.id})
        self.url_detail_b = reverse("profile", kwargs={"pk": self.user_b.id})

    def test_get_own_profile_success(self):
        resp = self.client_a.get(self.url_detail_a)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        data = resp.data
        # Pflichtfelder
        for f in ["user", "username", "email", "type", "created_at"]:
            self.assertIn(f, data)
        # nie null
        for f in ["first_name", "last_name", "location", "tel", "description", "working_hours"]:
            self.assertIsNotNone(data[f])
        self.assertEqual(data["type"], "business")
        self.assertEqual(data["username"], "user_a")
        self.assertEqual(data["email"], "a@mail.de")

    def test_get_foreign_profile_authenticated(self):
        # User A liest Profil von B (erlaubt, nur Auth nötig)
        resp = self.client_a.get(self.url_detail_b)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["user"], self.user_b.id)
        self.assertEqual(resp.data["type"], "customer")

    def test_unauthenticated_gets_401(self):
        resp = self.anon.get(self.url_detail_a)
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_non_existing_profile_returns_404(self):
        url = reverse("profile", kwargs={"pk": 999999})
        resp = self.client_a.get(url)
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_no_null_fields_in_response(self):
        # User B hat viele leere Felder -> Response darf trotzdem keine nulls haben
        resp = self.client_b.get(self.url_detail_b)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        for f in ["first_name", "last_name", "location", "tel", "description", "working_hours"]:
            self.assertIsNotNone(resp.data[f])  # erlaubt: "", aber nicht None
