from django.conf import settings
from django.db import models


class Offer(models.Model):
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="offers",
    )
    title = models.CharField(max_length=200)
    image = models.URLField(blank=True, null=True)
    description = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "offers"
        ordering = ["-id"]

    def __str__(self):
        return f"{self.title} (#{self.pk})"


class OfferDetail(models.Model):
    class OfferType(models.TextChoices):
        BASIC = "basic", "basic"
        STANDARD = "standard", "standard"
        PREMIUM = "premium", "premium"

    offer = models.ForeignKey(
        Offer, on_delete=models.CASCADE, related_name="details"
    )
    title = models.CharField(max_length=200)
    revisions = models.PositiveIntegerField(default=0)
    delivery_time_in_days = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    features = models.JSONField(default=list)
    offer_type = models.CharField(
        max_length=20, choices=OfferType.choices
    )

    class Meta:
        db_table = "offer_details"
        unique_together = ("offer", "offer_type")
        ordering = ["id"]

    def __str__(self):
        return f"{self.offer_type} for offer #{self.offer_id}"
