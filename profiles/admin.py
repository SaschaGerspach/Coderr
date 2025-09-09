from django.contrib import admin
from .models import Profile

@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    """
    Profile-Liste mit eigener ID + zugehöriger User-ID.
    """
    list_display = ("id", "user_id_display", "user", "type", "created_at")
    list_select_related = ("user",)
    search_fields = ("user__username", "user__email", "type")
    list_filter = ("type", "created_at")
    ordering = ("-created_at", "-id")
    autocomplete_fields = ("user",)
    readonly_fields = ("created_at",)

    def user_id_display(self, obj):
        return obj.user_id
    user_id_display.short_description = "user id"
    user_id_display.admin_order_field = "user__id"
