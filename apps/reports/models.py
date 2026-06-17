from decimal import Decimal

from django.conf import settings
from django.db import models
from django.utils import timezone


class DailyCloseout(models.Model):
    business_date = models.DateField(unique=True, db_index=True)
    service_sales_total = models.DecimalField(max_digits=12, decimal_places=0, default=0)
    product_sales_total = models.DecimalField(max_digits=12, decimal_places=0, default=0)
    cash_total = models.DecimalField(max_digits=12, decimal_places=0, default=0)
    mobile_money_total = models.DecimalField(max_digits=12, decimal_places=0, default=0)
    expenses_total = models.DecimalField(max_digits=12, decimal_places=0, default=0)
    cash_expenses_total = models.DecimalField(max_digits=12, decimal_places=0, default=0)
    commission_total = models.DecimalField(max_digits=12, decimal_places=0, default=0)
    expected_cash = models.DecimalField(max_digits=12, decimal_places=0, default=0)
    counted_cash = models.DecimalField(max_digits=12, decimal_places=0, default=0)
    mobile_money_reference = models.CharField(max_length=140, blank=True)
    pending_approvals_confirmed = models.BooleanField(default=False)
    expenses_confirmed = models.BooleanField(default=False)
    commissions_confirmed = models.BooleanField(default=False)
    mobile_money_confirmed = models.BooleanField(default=False)
    notes = models.TextField(blank=True)
    closed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="daily_closeouts",
    )
    closed_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-business_date"]
        indexes = [
            models.Index(fields=["business_date", "closed_at"]),
        ]

    def __str__(self):
        return f"Daily closeout for {self.business_date}"

    @property
    def total_sales(self):
        return (self.service_sales_total or Decimal("0")) + (self.product_sales_total or Decimal("0"))

    @property
    def cash_variance(self):
        return (self.counted_cash or Decimal("0")) - (self.expected_cash or Decimal("0"))

    @property
    def variance_label(self):
        variance = self.cash_variance
        if variance > 0:
            return "Surplus"
        if variance < 0:
            return "Shortage"
        return "Balanced"
