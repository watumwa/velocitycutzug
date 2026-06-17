from decimal import Decimal

from django.conf import settings
from django.db import models
from django.utils import timezone


class Expense(models.Model):
    class Category(models.TextChoices):
        RENT = "rent", "Rent"
        UTILITIES = "utilities", "Utilities"
        ELECTRICITY = "electricity", "Electricity"
        WATER = "water", "Water"
        INTERNET = "internet", "Internet / Airtime"
        SALARIES = "salaries", "Salaries / Allowances"
        INVENTORY = "inventory", "Stock Purchase / Supplies"
        CLEANING = "cleaning", "Cleaning"
        TRANSPORT = "transport", "Transport"
        MARKETING = "marketing", "Marketing"
        REPAIRS = "repairs", "Repairs & Maintenance"
        EQUIPMENT = "equipment", "Equipment Purchase"
        WELFARE = "welfare", "Staff Welfare / Lunch"
        SECURITY = "security", "Security"
        TAXES = "taxes", "Taxes / Licences"
        OTHER = "other", "Other"

    class PaymentMethod(models.TextChoices):
        CASH = "cash", "Cash"
        MOBILE_MONEY = "mobile_money", "Mobile Money"
        BANK = "bank", "Bank Transfer"
        CARD = "card", "Card"
        OTHER = "other", "Other"

    title = models.CharField(max_length=140)
    category = models.CharField(max_length=30, choices=Category.choices, default=Category.OTHER, db_index=True)
    amount = models.DecimalField(max_digits=12, decimal_places=0)
    expense_date = models.DateField(default=timezone.localdate, db_index=True)
    vendor = models.CharField(max_length=120, blank=True, help_text="Supplier, landlord, staff member, or payee.")
    payment_method = models.CharField(max_length=30, choices=PaymentMethod.choices, default=PaymentMethod.CASH)
    receipt_number = models.CharField(max_length=80, blank=True)
    notes = models.TextField(blank=True)
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="recorded_expenses",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-expense_date", "-created_at", "-id"]
        indexes = [
            models.Index(fields=["expense_date", "category"]),
        ]

    def __str__(self) -> str:
        return f"{self.title} - UGX {self.amount:,.0f}"

    @property
    def amount_decimal(self):
        return self.amount or Decimal("0")
