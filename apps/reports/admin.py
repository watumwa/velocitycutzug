from django.contrib import admin

from .models import DailyCloseout


@admin.register(DailyCloseout)
class DailyCloseoutAdmin(admin.ModelAdmin):
    list_display = ("business_date", "expected_cash", "counted_cash", "cash_variance", "closed_by", "closed_at")
    list_filter = ("business_date", "closed_at")
    search_fields = ("business_date", "closed_by__username", "closed_by__first_name", "closed_by__last_name", "notes")
    readonly_fields = (
        "business_date",
        "service_sales_total",
        "product_sales_total",
        "cash_total",
        "mobile_money_total",
        "expenses_total",
        "cash_expenses_total",
        "commission_total",
        "expected_cash",
        "closed_by",
        "closed_at",
        "updated_at",
    )
