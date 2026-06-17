from django.contrib import admin

from .models import Expense


@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ("expense_date", "title", "category", "vendor", "payment_method", "amount", "recorded_by")
    list_filter = ("category", "payment_method", "expense_date")
    search_fields = ("title", "vendor", "receipt_number", "notes")
    autocomplete_fields = ("recorded_by",)
