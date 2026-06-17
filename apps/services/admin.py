from django.contrib import admin

from .models import Service


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ("name", "price", "support_commission_enabled", "support_commission_amount", "is_active", "has_photo")
    list_filter = ("is_active", "support_commission_enabled")
    search_fields = ("name",)

    @admin.display(boolean=True)
    def has_photo(self, obj):
        return bool(obj.photo)
