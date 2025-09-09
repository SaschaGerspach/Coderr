from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

User = get_user_model()

# Falls User bereits registriert ist, zuerst deregistrieren (idempotent).
try:
    admin.site.unregister(User)
except admin.sites.NotRegistered:
    pass


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    """
    User-Liste inkl. ID, Profil-Typ (Profile.type) und Admin-Flags.
    """
    list_display = (
        "id",
        "username",
        "email",
        "profile_type_display",
        "is_staff",
        "is_superuser",
        "is_active",
        "date_joined",
        "last_login",
    )
    list_select_related = ("profile",)
    ordering = ("-date_joined", "-id")
    search_fields = ("username", "email", "profile__type")
    list_filter = ("is_staff", "is_superuser", "is_active", "profile__type")

    def profile_type_display(self, obj):
        prof = getattr(obj, "profile", None)
        return getattr(prof, "type", "") or ""
    profile_type_display.short_description = "profile type"
    profile_type_display.admin_order_field = "profile__type"
