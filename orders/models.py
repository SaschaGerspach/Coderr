from django.conf import settings
from django.db import models
from django.core.validators import MinValueValidator
from offers.models import OfferDetail


class Order(models.Model):
    class Status(models.TextChoices):
        IN_PROGRESS = "in_progress", "in_progress"
        # weitere Stati können später ergänzt werden (completed/cancelled etc.)

    # Beziehungen
    customer_user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="orders_placed"
    )
    business_user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="orders_received"
    )
    # Optional intern: Referenzen zur Quelle (nicht in der Response benötigt, aber praktisch)
    offer_detail = models.ForeignKey(OfferDetail, on_delete=models.PROTECT, related_name="orders", null=True, blank=True)

    # Snapshot-Felder aus dem OfferDetail
    title = models.CharField(max_length=200)
    revisions = models.IntegerField(validators=[MinValueValidator(0)])
    delivery_time_in_days = models.IntegerField(validators=[MinValueValidator(1)])
    price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    features = models.JSONField(default=list, blank=True)  # Liste aus Strings
    offer_type = models.CharField(max_length=20, choices=OfferDetail.OfferType.choices)

    # Status & Timestamps
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.IN_PROGRESS)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f"Order<{self.id} {self.title} {self.status}>"
