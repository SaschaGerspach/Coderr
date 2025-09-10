from django.contrib import admin
from django.utils.html import format_html
from .models import Order


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    """
    Übersichtliche Order-Verwaltung:
    - Liste: ID, Titel, Status (Badge), Customer, Business, Preis, Created
    - Filter: Status, Created (Date-Hierarchy)
    - Suche: Titel, Customer-Username, Business-Username
    - Readonly: Snapshot-Felder; Status ist editierbar
    """
    list_display = (
        "id",
        "title",
        "status_badge",
        "customer_username",
        "business_username",
        "price",
        "created_at",
        "updated_at",
    )
    list_select_related = ("customer_user", "business_user")
    list_filter = ("status", "created_at")
    date_hierarchy = "created_at"
    ordering = ("-created_at", "-id")
    search_fields = ("title", "customer_user__username", "business_user__username")

    # Nur Status darf im Admin geändert werden; alles andere ist Snapshot
    readonly_fields = (
        "customer_user",
        "business_user",
        "offer_detail",
        "title",
        "revisions",
        "delivery_time_in_days",
        "price",
        "features",
        "offer_type",
        "created_at",
        "updated_at",
    )
    fields = (
        "status",
        "customer_user",
        "business_user",
        "offer_detail",
        "title",
        "revisions",
        "delivery_time_in_days",
        "price",
        "features",
        "offer_type",
        "created_at",
        "updated_at",
    )

    # Badges & Shortcuts
    def status_badge(self, obj):
        color = {
            "in_progress": "#0ea5e9",
            "completed": "#22c55e",
            "cancelled": "#ef4444",
        }.get(obj.status, "#9ca3af")
        return format_html(
            '<span style="display:inline-block;padding:2px 8px;border-radius:999px;'
            'font-size:12px;font-weight:600;color:#fff;background:{};">{}</span>',
            color,
            obj.status,
        )
    status_badge.short_description = "status"
    status_badge.admin_order_field = "status"

    def customer_username(self, obj):
        return obj.customer_user.username if obj.customer_user_id else ""
    customer_username.short_description = "customer"

    def business_username(self, obj):
        return obj.business_user.username if obj.business_user_id else ""
    business_username.short_description = "business"
