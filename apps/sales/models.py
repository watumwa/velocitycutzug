from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from .services import calculate_commission, commission_from_rate, haircut_commission_rate_for_price


class Sale(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending Approval"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"
        CANCELLED = "cancelled", "Cancelled"

    class PaymentMethod(models.TextChoices):
        CASH = "cash", "Cash"
        MOBILE_MONEY = "mobile_money", "Mobile Money"

    customer = models.ForeignKey(
        "customers.Customer",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sales",
    )

    # Kept for backwards compatibility — reflects the first/primary employee
    employee = models.ForeignKey(
        "employees.Employee",
        on_delete=models.PROTECT,
        related_name="sales",
        null=True,
        blank=True,
    )

    service = models.ForeignKey(
        "services.Service",
        on_delete=models.PROTECT,
        related_name="sales",
        null=True,
        blank=True,
    )

    amount = models.DecimalField(max_digits=12, decimal_places=0)

    # Total approved commission across all items.
    # This includes the main employee commission and any support employee commission.
    # Pending/rejected/cancelled records stay at 0.
    commission_amount = models.DecimalField(max_digits=12, decimal_places=0, default=0)

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.APPROVED,
        db_index=True,
    )

    # Cashier/admin confirms this when approving a pending employee submission.
    # Existing records default to Cash for backwards compatibility.
    payment_method = models.CharField(
        max_length=20,
        choices=PaymentMethod.choices,
        default=PaymentMethod.CASH,
        db_index=True,
    )

    submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="submitted_sales",
    )

    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_sales",
    )

    approved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now, db_index=True)
    notes = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(fields=["status", "payment_method", "created_at"]),
        ]

    def __str__(self) -> str:
        customer_label = self.customer or "Walk-in"
        return f"{self.service_summary} for {customer_label}"

    @property
    def sale_items(self):
        return list(self.items.select_related("service", "employee", "support_employee").all())

    @property
    def is_approved(self) -> bool:
        return self.status == self.Status.APPROVED

    @property
    def is_pending(self) -> bool:
        return self.status == self.Status.PENDING

    @property
    def service_summary(self) -> str:
        names = []

        for item in self.sale_items:
            service = getattr(item, "service", None)
            if service and getattr(service, "name", None) and service.name not in names:
                names.append(service.name)

        if names:
            return ", ".join(names)

        service = getattr(self, "service", None)
        if service and getattr(service, "name", None):
            return service.name

        return "No service selected"

    @property
    def employee_summary(self) -> str:
        names = []

        for item in self.sale_items:
            employee = getattr(item, "employee", None)
            if employee and getattr(employee, "name", None) and employee.name not in names:
                names.append(employee.name)

            support_employee = getattr(item, "support_employee", None)
            if support_employee and getattr(support_employee, "name", None) and support_employee.name not in names:
                names.append(support_employee.name)

        if names:
            return ", ".join(names)

        employee = getattr(self, "employee", None)
        if employee and getattr(employee, "name", None):
            return employee.name

        return "Unassigned"

    @property
    def main_commission_amount(self):
        return sum((item.commission_amount or Decimal("0") for item in self.sale_items), Decimal("0"))

    @property
    def support_commission_amount(self):
        return sum((item.support_commission_amount or Decimal("0") for item in self.sale_items), Decimal("0"))

    @property
    def item_count(self) -> int:
        items = self.sale_items
        if items:
            return len(items)
        return 1 if self.service_id else 0

    def clean(self):
        if self.amount is not None and self.amount < 0:
            raise ValidationError({"amount": "Amount cannot be negative."})

    def recalculate_commission(self):
        """Sum main + support commission from approved items and update the sale total."""
        if not self.is_approved:
            total = Decimal("0")
            self.items.update(commission_amount=0, support_commission_amount=0)
        else:
            total = Decimal("0")
            for item in self.items.select_related("service", "employee", "support_employee"):
                item.commission_amount = item.calculate_commission_amount()
                item.support_commission_amount = item.calculate_support_commission_amount()
                item.save(update_fields=["commission_rate", "commission_amount", "support_commission_amount"])
                total += (item.commission_amount or Decimal("0")) + (item.support_commission_amount or Decimal("0"))

        self.commission_amount = total
        Sale.objects.filter(pk=self.pk).update(commission_amount=total)
        return total

    def approve(self, user=None, payment_method=None, support_assignments=None):
        """
        Approve a pending sale. Cashier/admin may pass:
        - payment_method: cash or mobile_money
        - support_assignments: dict mapping SaleItem id to support employee id.
        """
        if payment_method in {choice[0] for choice in self.PaymentMethod.choices}:
            self.payment_method = payment_method

        self.status = self.Status.APPROVED
        self.approved_by = user
        self.approved_at = timezone.now()
        self.save(update_fields=["status", "payment_method", "approved_by", "approved_at"])

        if support_assignments:
            for item in self.items.select_related("service", "employee"):
                support_employee_id = support_assignments.get(str(item.pk)) or support_assignments.get(item.pk)
                if not support_employee_id:
                    item.support_employee = None
                    item.support_commission_amount = 0
                    item.save(update_fields=["support_employee", "support_commission_amount"])
                    continue

                try:
                    support_employee_id = int(support_employee_id)
                except (TypeError, ValueError):
                    support_employee_id = None

                if support_employee_id and support_employee_id != item.employee_id:
                    item.support_employee_id = support_employee_id
                else:
                    item.support_employee = None
                item.save(update_fields=["support_employee"])

        self.recalculate_commission()

    def reject(self, user=None):
        self.status = self.Status.REJECTED
        self.approved_by = user
        self.approved_at = timezone.now()
        self.commission_amount = 0
        self.save(update_fields=["status", "approved_by", "approved_at", "commission_amount"])
        self.items.update(commission_amount=0, support_commission_amount=0)

    def save(self, *args, **kwargs):
        if self.created_at is None:
            self.created_at = timezone.now()

        if self.status == self.Status.APPROVED and self.approved_at is None:
            self.approved_at = timezone.now()

        if self.status != self.Status.APPROVED:
            self.commission_amount = 0

        super().save(*args, **kwargs)


class SaleItem(models.Model):
    sale = models.ForeignKey(Sale, on_delete=models.CASCADE, related_name="items")

    # Main service done.
    service = models.ForeignKey(
        "services.Service",
        on_delete=models.PROTECT,
        related_name="sale_items",
    )

    # Main employee who gets normal percentage/default commission.
    employee = models.ForeignKey(
        "employees.Employee",
        on_delete=models.PROTECT,
        related_name="sale_items",
        null=True,
        blank=True,
    )

    # Optional second/support employee who gets a fixed commission configured on the service.
    support_employee = models.ForeignKey(
        "employees.Employee",
        on_delete=models.PROTECT,
        related_name="support_sale_items",
        null=True,
        blank=True,
    )

    price = models.DecimalField(max_digits=12, decimal_places=0)

    commission_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Override main employee commission %. Leave blank to use employee/default service rate.",
    )

    # Main employee commission.
    commission_amount = models.DecimalField(max_digits=12, decimal_places=0, default=0)

    # Fixed commission paid to the support employee.
    support_commission_amount = models.DecimalField(max_digits=12, decimal_places=0, default=0)

    class Meta:
        ordering = ["id"]
        constraints = [
            models.UniqueConstraint(
                fields=["sale", "service"],
                name="unique_sale_service_item",
            )
        ]

    def __str__(self) -> str:
        service = getattr(self, "service", None)
        service_name = service.name if service else "No service"
        return f"{service_name} on sale #{self.sale_id}"

    @property
    def total_commission_amount(self):
        return (self.commission_amount or Decimal("0")) + (self.support_commission_amount or Decimal("0"))

    def calculate_commission_amount(self):
        if not self.employee_id or self.price is None:
            return Decimal("0")

        auto_rate = haircut_commission_rate_for_price(self.service, self.price)
        rate = self.commission_rate if self.commission_rate is not None else auto_rate

        if rate is not None:
            self.commission_rate = rate
            return commission_from_rate(self.price, rate)

        return calculate_commission(self.employee, self.price)

    def calculate_support_commission_amount(self):
        if not self.support_employee_id or not self.service_id:
            return Decimal("0")
        if self.employee_id and self.support_employee_id == self.employee_id:
            return Decimal("0")
        if not getattr(self.service, "support_commission_enabled", False):
            return Decimal("0")
        return Decimal(getattr(self.service, "support_commission_amount", 0) or 0)

    def save(self, *args, **kwargs):
        if self.sale_id and self.sale.status != Sale.Status.APPROVED:
            self.commission_amount = Decimal("0")
            self.support_commission_amount = Decimal("0")
        else:
            if self.employee_id and self.price is not None:
                self.commission_amount = self.calculate_commission_amount()
            else:
                self.commission_amount = Decimal("0")
            self.support_commission_amount = self.calculate_support_commission_amount()

        super().save(*args, **kwargs)
