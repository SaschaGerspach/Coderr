from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from offers.models import Offer, OfferDetail
from profiles.models import Profile
from reviews.models import Review


User = get_user_model()


class BaseInfoAPITests(TestCase):
    """
    Tests for GET /api/base-info/

    Requirements:
    - No authentication required (AllowAny).
    - Returns counts for reviews, business profiles, offers.
    - Returns average rating rounded to 1 decimal; 0.0 if no reviews.
    """

    def setUp(self):
        self.client = APIClient()
        self.url = reverse("base-info")

    def test_public_access_allowed_200(self):
        """Endpoint must be publicly accessible and return 200."""
        res = self.client.get(self.url)
        self.assertEqual(res.status_code, 200)
        self.assertIn("review_count", res.data)
        self.assertIn("average_rating", res.data)
        self.assertIn("business_profile_count", res.data)
        self.assertIn("offer_count", res.data)

    def test_no_data_returns_zeros(self):
        """With no rows in DB, all counters are zero and average_rating is 0.0."""
        res = self.client.get(self.url)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["review_count"], 0)
        self.assertEqual(res.data["average_rating"], 0.0)
        self.assertEqual(res.data["business_profile_count"], 0)
        self.assertEqual(res.data["offer_count"], 0)

    def test_counts_and_average_rating(self):
        """Populate minimal data and verify counts + rounded average."""
        # Create users + profiles
        biz = User.objects.create_user(username="biz", password="x")
        cust = User.objects.create_user(username="cust", password="x")
        Profile.objects.create(user=biz, type="business")
        Profile.objects.create(user=cust, type="customer")

        # Offer owned by business (1 offer)
        offer = Offer.objects.create(owner=biz, title="Logo", image=None, description="")
        OfferDetail.objects.create(
            offer=offer,
            title="Basic",
            revisions=1,
            delivery_time_in_days=3,
            price="99.00",
            features=["a"],
            offer_type=OfferDetail.OfferType.BASIC,
        )
        OfferDetail.objects.create(
            offer=offer,
            title="Standard",
            revisions=2,
            delivery_time_in_days=5,
            price="149.00",
            features=["b"],
            offer_type=OfferDetail.OfferType.STANDARD,
        )
        OfferDetail.objects.create(
            offer=offer,
            title="Premium",
            revisions=3,
            delivery_time_in_days=7,
            price="199.00",
            features=["c"],
            offer_type=OfferDetail.OfferType.PREMIUM,
        )

        # Reviews: average of [4, 5] => 4.5
        Review.objects.create(business_user=biz, reviewer=cust, rating=4, description="")
        other = User.objects.create_user(username="cust2", password="x")
        Profile.objects.create(user=other, type="customer")
        Review.objects.create(business_user=biz, reviewer=other, rating=5, description="")

        res = self.client.get(self.url)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["review_count"], 2)
        self.assertEqual(res.data["business_profile_count"], 1)
        self.assertEqual(res.data["offer_count"], 1)
        self.assertEqual(res.data["average_rating"], 4.5)

    def test_average_is_rounded_to_one_decimal(self):
        """Non-integer averages must be rounded to one decimal place."""
        biz = User.objects.create_user(username="biz2", password="x")
        cust1 = User.objects.create_user(username="c1", password="x")
        cust2 = User.objects.create_user(username="c2", password="x")
        Profile.objects.create(user=biz, type="business")
        Profile.objects.create(user=cust1, type="customer")
        Profile.objects.create(user=cust2, type="customer")

        # 4 and 3 => average 3.5 (exactly one decimal already)
        Review.objects.create(business_user=biz, reviewer=cust1, rating=4, description="")
        Review.objects.create(business_user=biz, reviewer=cust2, rating=3, description="")

        res = self.client.get(self.url)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["average_rating"], 3.5)
