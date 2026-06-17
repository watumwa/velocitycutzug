from decimal import Decimal

from django import forms

from apps.customers.models import Customer

from .models import Product, ProductSale, StockEntry


class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = [
            "name",
            "category",
            "product_type",
            "unit",
            "buying_price",
            "selling_price",
            "low_stock_threshold",
            "supplier",
            "expiry_date",
            "is_active",
        ]
        widgets = {
            "name": forms.TextInput(attrs={"placeholder": "e.g. Hair Relaxer, Beard Oil, Gloves"}),
            "unit": forms.TextInput(attrs={"placeholder": "e.g. bottle, ml, pcs"}),
            "buying_price": forms.NumberInput(attrs={"min": "0", "step": "1"}),
            "selling_price": forms.NumberInput(attrs={"min": "0", "step": "1"}),
            "low_stock_threshold": forms.NumberInput(attrs={"min": "0"}),
            "supplier": forms.TextInput(attrs={"placeholder": "Main supplier, optional"}),
            "expiry_date": forms.DateInput(attrs={"type": "date"}),
        }


class StockEntryForm(forms.ModelForm):
    create_expense = forms.BooleanField(
        required=False,
        initial=True,
        label="Record stock purchase as expense",
        help_text="For restocks, this creates an expense using quantity × unit cost.",
    )

    class Meta:
        model = StockEntry
        fields = ["product", "entry_type", "quantity", "unit_cost", "supplier", "note", "date"]
        widgets = {
            "date": forms.DateInput(attrs={"type": "date"}),
            "note": forms.TextInput(attrs={"placeholder": "Optional note"}),
            "quantity": forms.NumberInput(attrs={"min": "1", "step": "1"}),
            "unit_cost": forms.NumberInput(attrs={"min": "0", "step": "1"}),
            "supplier": forms.TextInput(attrs={"placeholder": "Supplier / source"}),
        }

    def __init__(self, *args, product=None, **kwargs):
        super().__init__(*args, **kwargs)
        if product:
            self.fields["product"].initial = product
            self.fields["product"].widget = forms.HiddenInput()
            self.fields["unit_cost"].initial = product.buying_price
            self.fields["supplier"].initial = product.supplier
        else:
            self.fields["product"].queryset = Product.objects.filter(is_active=True)

    def clean_quantity(self):
        qty = self.cleaned_data.get("quantity")
        entry_type = self.cleaned_data.get("entry_type")
        if qty is None:
            return qty
        if qty == 0:
            raise forms.ValidationError("Quantity cannot be zero.")
        if entry_type == StockEntry.EntryType.RESTOCK:
            return abs(qty)
        if entry_type in StockEntry.STOCK_OUT_TYPES:
            return -abs(qty)
        return qty

    def clean(self):
        cleaned = super().clean()
        entry_type = cleaned.get("entry_type")
        quantity = cleaned.get("quantity") or 0
        unit_cost = cleaned.get("unit_cost") or Decimal("0")
        product = cleaned.get("product")
        if entry_type == StockEntry.EntryType.RESTOCK and unit_cost < 0:
            self.add_error("unit_cost", "Unit cost cannot be negative.")
        if product and entry_type in StockEntry.STOCK_OUT_TYPES and abs(quantity) > product.current_stock:
            self.add_error("quantity", f"Only {product.current_stock} {product.unit} available in stock.")
        return cleaned


class ProductSaleForm(forms.ModelForm):
    class Meta:
        model = ProductSale
        fields = ["product", "customer", "quantity", "unit_price", "payment_method", "sale_date", "notes"]
        widgets = {
            "quantity": forms.NumberInput(attrs={"min": "1", "step": "1"}),
            "unit_price": forms.NumberInput(attrs={"min": "0", "step": "1"}),
            "payment_method": forms.Select(),
            "sale_date": forms.DateInput(attrs={"type": "date"}),
            "notes": forms.TextInput(attrs={"placeholder": "Optional note"}),
        }

    def __init__(self, *args, product=None, **kwargs):
        super().__init__(*args, **kwargs)
        saleable = Product.objects.filter(is_active=True, product_type__in=[Product.ProductType.RETAIL, Product.ProductType.BOTH])
        self.fields["product"].queryset = saleable
        self.fields["customer"].queryset = Customer.objects.all()
        self.fields["customer"].required = False
        self.fields["customer"].empty_label = "Walk-in / No customer"
        if product:
            self.fields["product"].initial = product
            self.fields["product"].widget = forms.HiddenInput()
            self.fields["unit_price"].initial = product.selling_price
        elif not self.is_bound:
            first = saleable.first()
            if first:
                self.fields["unit_price"].initial = first.selling_price

    def clean(self):
        cleaned = super().clean()
        product = cleaned.get("product")
        quantity = cleaned.get("quantity") or 0
        unit_price = cleaned.get("unit_price") or Decimal("0")
        if product and not product.can_be_sold:
            self.add_error("product", "This item is salon-use only and cannot be sold.")
        if product and quantity > product.current_stock:
            self.add_error("quantity", f"Only {product.current_stock} {product.unit} available in stock.")
        if unit_price <= 0:
            self.add_error("unit_price", "Selling price must be greater than zero.")
        return cleaned
