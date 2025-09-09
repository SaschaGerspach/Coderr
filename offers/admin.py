from django.contrib import admin
from django.db.models import Min
from .models import Offer, OfferDetail


class OfferDetailInline(admin.TabularInline):
    """
    Zeigt die 3 OfferDetails direkt im Offer-Form an (Inline-Editing).
    """
    model = OfferDetail
    extra = 0
    fields = ("offer_type", "title", "price", "delivery_time_in_days", "revisions", "features")
    show_change_link = True


@admin.register(Offer)
class OfferAdmin(admin.ModelAdmin):
    """
    Komfortable Verwaltung von Offers:
    - Inline-Editing der Details
    - Such-/Filterfelder
    - Min-Preis und minimale Lieferzeit als Spalten & Readonly
    - performant via select_related + annotate
    """
    inlines = [OfferDetailInline]

    list_display = (
        "id",
        "title",
        "owner_username",
        "min_price_display",
        "min_delivery_time_display",
        "updated_at",
    )
    list_select_related = ("owner",)  # vermeidet N+1 bei Owner
    search_fields = ("title", "description", "owner__username", "owner__email")
    list_filter = ("updated_at",)
    date_hierarchy = "created_at"
    ordering = ("-updated_at", "-id")
    readonly_fields = ("created_at", "updated_at", "min_price_display", "min_delivery_time_display")
    autocomplete_fields = ("owner",)  # praktisch bei vielen Usern

    def get_queryset(self, request):
        # Min-Werte direkt in der Liste berechnen (keine N+1 auf Details)
        qs = super().get_queryset(request)
        return qs.select_related("owner").annotate(
            _min_price=Min("details__price"),
            _min_delivery=Min("details__delivery_time_in_days"),
        )

    def owner_username(self, obj):
        return obj.owner.username if obj.owner_id else ""
    owner_username.short_description = "owner"

    def min_price_display(self, obj):
        v = getattr(obj, "_min_price", None)
        return f"{v:.2f}" if v is not None else "-"
    min_price_display.short_description = "min price"

    def min_delivery_time_display(self, obj):
        v = getattr(obj, "_min_delivery", None)
        return v if v is not None else "-"
    min_delivery_time_display.short_description = "min delivery (days)"


@admin.register(OfferDetail)
class OfferDetailAdmin(admin.ModelAdmin):
    """
    Separater Admin für OfferDetails (falls man Details auch isoliert durchsuchen will).
    """
    list_display = ("id", "offer", "offer_type", "title", "price", "delivery_time_in_days", "revisions")
    list_select_related = ("offer", "offer__owner")
    search_fields = ("title", "offer__title", "offer__owner__username")
    list_filter = ("offer_type",)
    ordering = ("offer", "id")
