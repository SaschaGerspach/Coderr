from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase, APIClient
from rest_framework.authtoken.models import Token

from profiles.models import Profile

User = get_user_model()

class ProfilePatchTests(APITestCase):
    def setUp(self):
        # Users
        self.user_a = User.objects.create_user(
            username="owner", email="owner@mail.de", password="Pass123!"
        )
        self.user_b = User.objects.create_user(
            username="other", email="other@mail.de", password="Pass123!"
        )
        # Profiles
        self.profile_a = Profile.objects.create(user=self.user_a)
        self.profile_b = Profile.objects.create(user=self.user_b, type="business")

        # Clients
        self.client_owner = APIClient()
        self.client_owner.credentials(HTTP_AUTHORIZATION="Token " + Token.objects.create(user=self.user_a).key)

        self.client_other = APIClient()
        self.client_other.credentials(HTTP_AUTHORIZATION="Token " + Token.objects.create(user=self.user_b).key)

        self.client_anon = APIClient()

        self.url_owner = reverse("profile-partial-update", kwargs={"pk": self.user_a.id})
        self.url_other = reverse("profile-partial-update", kwargs={"pk": self.user_b.id})

    def test_owner_can_patch_profile(self):
        payload = {
            "first_name": "Max",
            "last_name": "Mustermann",
            "location": "Berlin",
            "tel": "987654321",
            "description": "Updated business description",
            "working_hours": "10-18",
            "email": "new_email@business.de"
        }
        resp = self.client_owner.patch(self.url_owner, payload, format="json")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

        data = resp.data
        self.assertEqual(data["first_name"], "Max")
        self.assertEqual(data["last_name"], "Mustermann")
        self.assertEqual(data["location"], "Berlin")
        self.assertEqual(data["tel"], "987654321")
        self.assertEqual(data["description"], "Updated business description")
        self.assertEqual(data["working_hours"], "10-18")
        self.assertEqual(data["email"], "new_email@business.de")
        self.assertEqual(data["username"], "owner")
        self.assertIn("created_at", data)

        # DB tatsächlich aktualisiert?
        self.user_a.refresh_from_db()
        self.profile_a.refresh_from_db()
        self.assertEqual(self.user_a.first_name, "Max")
        self.assertEqual(self.user_a.last_name, "Mustermann")
        self.assertEqual(self.user_a.email, "new_email@business.de")
        self.assertEqual(self.profile_a.location, "Berlin")

    def test_forbidden_when_patching_foreign_profile(self):
        payload = {"location": "Hamburg"}
        resp = self.client_owner.patch(self.url_other, payload, format="json")
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_unauthenticated_gets_401(self):
        resp = self.client_anon.patch(self.url_owner, {"location": "Köln"}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_null_values_are_coalesced_to_empty_strings_in_response(self):
        # Felder laut Spez nie null im Response
        payload = {
            "first_name": None,
            "last_name": None,
            "location": None,
            "tel": None,
            "description": None,
            "working_hours": None,
        }
        resp = self.client_owner.patch(self.url_owner, payload, format="json")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        for f in ["first_name", "last_name", "location", "tel", "description", "working_hours"]:
            self.assertEqual(resp.data.get(f), "")

    def test_invalid_email_returns_400(self):
        resp = self.client_owner.patch(self.url_owner, {"email": "not-an-email"}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("email", str(resp.data))

class ProfilePatchLazyCreateTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="owner2", email="o2@mail.de", password="Pass123!")
        # hier ABSICHTLICH KEIN Profile anlegen (lazy-create testen)
        self.client_auth = APIClient()
        self.client_auth.credentials(HTTP_AUTHORIZATION="Token " + Token.objects.create(user=self.user).key)
        self.url = reverse("profile-partial-update", kwargs={"pk": self.user.id})

    def test_owner_patch_creates_profile_if_missing(self):
        self.assertFalse(Profile.objects.filter(user=self.user).exists())  # Vorbedingung
        payload = {"location": "Berlin", "first_name": "Max"}
        resp = self.client_auth.patch(self.url, payload, format="json")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

        # Profil wurde angelegt und aktualisiert
        self.assertTrue(Profile.objects.filter(user=self.user).exists())
        prof = Profile.objects.get(user=self.user)
        self.assertEqual(prof.location, "Berlin")
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, "Max")

class ProfilePatchPermissionTests(APITestCase):
    def setUp(self):
        # Normaler User A
        self.user_a = User.objects.create_user(username="user_a", email="a@mail.de", password="Pass123!")
        self.profile_a = Profile.objects.create(user=self.user_a)

        # Ziel-User B (dessen Profil NICHT geändert werden darf)
        self.user_b = User.objects.create_user(username="user_b", email="b@mail.de", password="Pass123!")
        self.profile_b = Profile.objects.create(user=self.user_b)

        # Staff-User
        self.staff_user = User.objects.create_user(username="staff_user", email="staff@mail.de", password="Pass123!", is_staff=True)
        self.staff_profile = Profile.objects.create(user=self.staff_user)
        self.staff_client = APIClient()
        self.staff_client.credentials(HTTP_AUTHORIZATION="Token " + Token.objects.create(user=self.staff_user).key)

        # Superuser
        self.admin_user = User.objects.create_superuser(username="admin_user", email="admin@mail.de", password="Pass123!")
        self.admin_profile = Profile.objects.create(user=self.admin_user)
        self.admin_client = APIClient()
        self.admin_client.credentials(HTTP_AUTHORIZATION="Token " + Token.objects.create(user=self.admin_user).key)

        # URL auf Profil von user_b
        self.url_user_b = reverse("profile-partial-update", kwargs={"pk": self.user_b.id})

    def test_staff_cannot_patch_foreign_profile(self):
        resp = self.staff_client.patch(self.url_user_b, {"location": "Berlin"}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_cannot_patch_foreign_profile(self):
        resp = self.admin_client.patch(self.url_user_b, {"location": "Hamburg"}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)


class ProfilePatchExistencePolicyTests(APITestCase):
    def setUp(self):
        # Owner A (mit Profil)
        self.user_a = User.objects.create_user(username="owner_a", email="a@mail.de", password="Pass123!")
        self.profile_a = Profile.objects.create(user=self.user_a)
        self.client_owner_a = APIClient()
        self.client_owner_a.credentials(HTTP_AUTHORIZATION="Token " + Token.objects.create(user=self.user_a).key)

    def test_owner_lazy_create_when_missing(self):
        # Owner B hat noch KEIN Profil -> erster PATCH soll es anlegen (200)
        user_b = User.objects.create_user(username="owner_b", email="b@mail.de", password="Pass123!")
        client_b = APIClient()
        client_b.credentials(HTTP_AUTHORIZATION="Token " + Token.objects.create(user=user_b).key)
        url = reverse("profile-partial-update", kwargs={"pk": user_b.id})

        resp = client_b.patch(url, {"location": "Berlin"}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertTrue(Profile.objects.filter(user=user_b, location="Berlin").exists())

    def test_non_owner_never_learns_existence(self):
        # Authentifizierter Nicht-Owner → immer 403 (egal ob Profil existiert)
        url_nonexistent = reverse("profile-partial-update", kwargs={"pk": 999999})
        resp = self.client_owner_a.patch(url_nonexistent, {"location": "Bremen"}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_unauthenticated_gets_401_before_lookup(self):
        # Unauthentifiziert → 401
        anon = APIClient()
        url = reverse("profile-partial-update", kwargs={"pk": self.user_a.id})
        resp = anon.patch(url, {"location": "Köln"}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)