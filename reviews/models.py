"""Reviews app models.

Defines the Review model. A user (reviewer) can leave at most one review
per business user. Ratings are constrained between 1 and 5.
"""

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class Review(models.Model):
    """Represents a review written by a user for a business user."""

    business_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="reviews_received",
    )
    reviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="reviews_written",
    )

    rating = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    description = models.TextField(blank=True, default="")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["business_user", "reviewer"],
                name="unique_review_per_business_and_reviewer",
            )
        ]
        ordering = ("-created_at", "-id")

    def __str__(self) -> str:
        """Readable representation for admin and debugging."""
        return (
            f"Review<{self.id} {self.reviewer_id}->{self.business_user_id} "
            f"{self.rating}>"
        )
