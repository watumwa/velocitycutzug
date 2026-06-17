from django.contrib import admin

from .models import Product, ProductSale, StockEntry


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "product_type", "current_stock", "unit", "buying_price", "selling_price", "low_stock_threshold", "is_active")
    list_filter = ("category", "product_type", "is_active")
    search_fields = ("name", "supplier")


@admin.register(StockEntry)
class StockEntryAdmin(admin.ModelAdmin):
    list_display = ("date", "product", "entry_type", "quantity", "unit_cost", "supplier", "related_expense")
    list_filter = ("entry_type", "date")
    search_fields = ("product__name", "supplier", "note")
    autocomplete_fields = ("product", "related_expense")


@admin.register(ProductSale)
class ProductSaleAdmin(admin.ModelAdmin):
    list_display = ("sale_date", "product", "quantity", "unit_price", "total_amount", "payment_method", "customer", "sold_by")
    list_filter = ("sale_date", "payment_method", "product")
    search_fields = ("product__name", "customer__name", "notes")
    autocomplete_fields = ("product", "customer", "sold_by", "stock_entry")
