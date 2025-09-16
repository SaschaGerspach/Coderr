"""Orders app models.

Defines the Order model. An Order is created from an OfferDetail and snapshots
the key commercial fields (title, price, delivery time, features, offer type)
to remain stable even if the Offer changes later.
"""

from django.conf import settings
from django.db import models
from django.core.validators import MinValueValidator
from offers.models import OfferDetail


class Order(models.Model):
    """Represents a placed order between a customer and a business user."""

    class Status(models.TextChoices):
        IN_PROGRESS = "in_progress", "in_progress"
        COMPLETED = "completed", "completed"
        CANCELLED = "cancelled", "cancelled"

    customer_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="orders_placed",
    )
    business_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="orders_received",
    )
    offer_detail = models.ForeignKey(
        OfferDetail,
        on_delete=models.PROTECT,
        related_name="orders",
        null=True,
        blank=True,
    )

    title = models.CharField(max_length=200)
    revisions = models.IntegerField(validators=[MinValueValidator(0)])
    delivery_time_in_days = models.IntegerField(validators=[MinValueValidator(1)])
    price = models.DecimalField(
        max_digits=10, decimal_places=2, validators=[MinValueValidator(0)]
    )
    features = models.JSONField(default=list, blank=True)
    offer_type = models.CharField(
        max_length=20, choices=OfferDetail.OfferType.choices
    )

    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.IN_PROGRESS
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        """Readable representation for admin and debugging."""
        return f"Order<{self.id} {self.title} {self.status}>"
