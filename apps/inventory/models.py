from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from apps.core.models import TimeStampedModel


class Product(TimeStampedModel):
    class Category(models.TextChoices):
        HAIR_CARE = "hair_care", "Hair Care"
        BEARD_CARE = "beard_care", "Beard Care"
        NAILS = "nails", "Nails / Pedicure"
        CLEANING = "cleaning", "Cleaning Supplies"
        TOOLS = "tools", "Tools & Equipment"
        CONSUMABLES = "consumables", "Salon Consumables"
        COSMETICS = "cosmetics", "Cosmetics"
        OTHER = "other", "Other"

    class ProductType(models.TextChoices):
        RETAIL = "retail", "For Sale"
        CONSUMABLE = "consumable", "Salon Use Only"
        BOTH = "both", "Sale + Salon Use"

    name = models.CharField(max_length=150)
    category = models.CharField(max_length=30, choices=Category.choices, default=Category.OTHER, db_index=True)
    product_type = models.CharField(max_length=20, choices=ProductType.choices, default=ProductType.RETAIL, db_index=True)
    unit = models.CharField(max_length=40, default="pcs", help_text="e.g. pcs, ml, kg, bottle")
    buying_price = models.DecimalField(max_digits=12, decimal_places=0, default=0, help_text="Cost price per unit in UGX.")
    selling_price = models.DecimalField(max_digits=12, decimal_places=0, default=0, help_text="Retail selling price per unit in UGX.")
    low_stock_threshold = models.PositiveIntegerField(
        default=5, help_text="Alert when stock falls at or below this level."
    )
    supplier = models.CharField(max_length=150, blank=True)
    expiry_date = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]
        indexes = [
            models.Index(fields=["category", "product_type"]),
            models.Index(fields=["is_active"]),
        ]

    def __str__(self):
        return self.name

    @property
    def current_stock(self):
        result = self.stock_entries.aggregate(total=models.Sum("quantity"))["total"]
        return result or 0

    @property
    def is_low_stock(self):
        return self.current_stock <= self.low_stock_threshold

    @property
    def is_out_of_stock(self):
        return self.current_stock <= 0

    @property
    def stock_cost_value(self):
        return Decimal(self.current_stock or 0) * (self.buying_price or Decimal("0"))

    @property
    def stock_retail_value(self):
        return Decimal(self.current_stock or 0) * (self.selling_price or Decimal("0"))

    @property
    def can_be_sold(self):
        return self.product_type in {self.ProductType.RETAIL, self.ProductType.BOTH}

    @property
    def can_be_used_for_service(self):
        return self.product_type in {self.ProductType.CONSUMABLE, self.ProductType.BOTH}


class StockEntry(TimeStampedModel):
    class EntryType(models.TextChoices):
        RESTOCK = "restock", "Stock In / Restock"
        SOLD = "sold", "Sold to Customer"
        SERVICE_USAGE = "service_usage", "Used for Service"
        DAMAGED = "damaged", "Damaged"
        EXPIRED = "expired", "Expired"
        LOST = "lost", "Lost"
        INTERNAL_USE = "internal_use", "Internal Use"
        ADJUSTMENT = "adjustment", "Adjustment"

    STOCK_OUT_TYPES = {EntryType.SOLD, EntryType.SERVICE_USAGE, EntryType.DAMAGED, EntryType.EXPIRED, EntryType.LOST, EntryType.INTERNAL_USE}

    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="stock_entries")
    entry_type = models.CharField(max_length=30, choices=EntryType.choices, default=EntryType.RESTOCK, db_index=True)
    # Positive = stock in, negative = stock out. The form normalizes most outflow entries automatically.
    quantity = models.IntegerField(help_text="Positive adds stock. Negative removes stock.")
    unit_cost = models.DecimalField(max_digits=12, decimal_places=0, default=0, blank=True, help_text="Cost per unit for stock-in entries.")
    supplier = models.CharField(max_length=150, blank=True)
    note = models.CharField(max_length=255, blank=True)
    date = models.DateField(default=timezone.localdate, db_index=True)
    related_expense = models.ForeignKey(
        "expenses.Expense",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="stock_entries",
        help_text="Automatically created expense for stock purchases when applicable.",
    )

    class Meta:
        ordering = ["-date", "-id"]
        indexes = [
            models.Index(fields=["date", "entry_type"]),
        ]

    def __str__(self):
        return f"{self.get_entry_type_display()} {self.quantity} × {self.product.name}"

    @property
    def signed_label(self):
        return f"+{self.quantity}" if self.quantity > 0 else str(self.quantity)

    @property
    def total_cost(self):
        if self.quantity <= 0:
            return Decimal("0")
        return Decimal(self.quantity) * (self.unit_cost or Decimal("0"))

    @property
    def is_stock_in(self):
        return self.quantity > 0

    @property
    def is_stock_out(self):
        return self.quantity < 0

    def clean(self):
        if self.entry_type == self.EntryType.RESTOCK and self.quantity <= 0:
            raise ValidationError({"quantity": "Restock quantity must be greater than zero."})
        if self.entry_type in self.STOCK_OUT_TYPES and self.quantity >= 0:
            raise ValidationError({"quantity": "Stock-out quantity must be negative."})


class ProductSale(TimeStampedModel):
    class PaymentMethod(models.TextChoices):
        CASH = "cash", "Cash"
        MOBILE_MONEY = "mobile_money", "Mobile Money"

    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name="product_sales")
    customer = models.ForeignKey(
        "customers.Customer",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="product_sales",
    )
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=12, decimal_places=0)
    total_amount = models.DecimalField(max_digits=12, decimal_places=0, default=0)
    payment_method = models.CharField(
        max_length=20,
        choices=PaymentMethod.choices,
        default=PaymentMethod.CASH,
        db_index=True,
    )
    sale_date = models.DateField(default=timezone.localdate, db_index=True)
    sold_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="product_sales_recorded",
    )
    stock_entry = models.OneToOneField(
        StockEntry,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="product_sale",
    )
    notes = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["-sale_date", "-created_at", "-id"]
        indexes = [
            models.Index(fields=["sale_date"]),
        ]

    def __str__(self):
        return f"{self.quantity} × {self.product.name}"

    def clean(self):
        if self.product_id and not self.product.can_be_sold:
            raise ValidationError({"product": "This product is marked as salon-use only and cannot be sold."})
        if self.quantity <= 0:
            raise ValidationError({"quantity": "Quantity must be greater than zero."})
        if self.product_id and not self.pk and self.quantity > self.product.current_stock:
            raise ValidationError({"quantity": "Not enough stock available for this sale."})

    def save(self, *args, **kwargs):
        self.total_amount = Decimal(self.quantity or 0) * (self.unit_price or Decimal("0"))
        super().save(*args, **kwargs)
