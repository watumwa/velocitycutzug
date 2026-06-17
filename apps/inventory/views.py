import logging
from datetime import timedelta
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import DecimalField, Q, Sum, Value
from django.db.models.functions import Coalesce
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from apps.accounts.permissions import CASHIER, role_required
from apps.core.modal import is_modal, modal_success, render_modal
from apps.expenses.models import Expense

from .forms import ProductForm, ProductSaleForm, StockEntryForm
from .models import Product, ProductSale, StockEntry

ZERO = Value(0, output_field=DecimalField(max_digits=12, decimal_places=0))
logger = logging.getLogger(__name__)


def _money_total(qs, field_name):
    return qs.aggregate(total=Coalesce(Sum(field_name), ZERO))["total"] or Decimal("0")


@login_required
@role_required(CASHIER)
def product_list(request):
    q = (request.GET.get("q") or "").strip()
    category = request.GET.get("category", "")
    product_type = request.GET.get("type", "")
    status = request.GET.get("status", "")

    products_qs = Product.objects.prefetch_related("stock_entries").all()
    if q:
        products_qs = products_qs.filter(
            Q(name__icontains=q)
            | Q(supplier__icontains=q)
            | Q(unit__icontains=q)
        )
    if category:
        products_qs = products_qs.filter(category=category)
    if product_type:
        products_qs = products_qs.filter(product_type=product_type)
    if status == "active":
        products_qs = products_qs.filter(is_active=True)
    elif status == "inactive":
        products_qs = products_qs.filter(is_active=False)

    products = list(products_qs)
    if status == "low":
        products = [p for p in products if p.is_low_stock and not p.is_out_of_stock]
    elif status == "out":
        products = [p for p in products if p.is_out_of_stock]

    all_products = list(Product.objects.prefetch_related("stock_entries").all())
    low_stock = [p for p in all_products if p.is_low_stock]
    out_stock = [p for p in all_products if p.is_out_of_stock]
    retail_products = [p for p in all_products if p.can_be_sold]
    consumables = [p for p in all_products if p.can_be_used_for_service]

    today = timezone.localdate()
    month_start = today.replace(day=1)
    product_sales_month = ProductSale.objects.filter(sale_date__gte=month_start, sale_date__lte=today)

    context = {
        "products": products,
        "all_product_count": len(all_products),
        "low_stock_count": len(low_stock),
        "low_stock": low_stock,
        "out_stock_count": len(out_stock),
        "retail_count": len(retail_products),
        "consumable_count": len(consumables),
        "stock_cost_value": sum((p.stock_cost_value for p in all_products), Decimal("0")),
        "stock_retail_value": sum((p.stock_retail_value for p in all_products), Decimal("0")),
        "month_product_sales": _money_total(product_sales_month, "total_amount"),
        "recent_entries": StockEntry.objects.select_related("product")[:12],
        "recent_product_sales": ProductSale.objects.select_related("product", "customer", "sold_by")[:10],
        "category_choices": Product.Category.choices,
        "type_choices": Product.ProductType.choices,
        "filter_q": q,
        "filter_category": category,
        "filter_type": product_type,
        "filter_status": status,
    }
    return render(request, "inventory/list.html", context)


@login_required
@role_required(CASHIER)
def product_create(request):
    form = ProductForm(request.POST or None)
    if form.is_valid():
        try:
            product = form.save()
        except Exception:
            logger.exception("Product creation failed")
            form.add_error(None, "Product could not be saved. Check the details and try again.")
        else:
            if is_modal(request):
                return modal_success("Product added.")
            messages.success(request, "Product added.")
            return redirect("inventory:list")
    ctx = {"form": form, "title": "Add Product", "is_create": True}
    if is_modal(request):
        return render_modal(request, "inventory/product_form.html", ctx)
    return render(request, "inventory/product_form.html", ctx)


@login_required
@role_required(CASHIER)
def product_edit(request, pk):
    product = get_object_or_404(Product, pk=pk)
    form = ProductForm(request.POST or None, instance=product)
    if form.is_valid():
        try:
            form.save()
        except Exception:
            logger.exception("Product update failed for product id=%s", product.pk)
            form.add_error(None, "Product could not be updated. Check the details and try again.")
        else:
            if is_modal(request):
                return modal_success(f"{product.name} updated.")
            messages.success(request, "Product updated.")
            return redirect("inventory:list")
    ctx = {"form": form, "product": product, "title": f"Edit — {product.name}", "is_create": False}
    if is_modal(request):
        return render_modal(request, "inventory/product_form.html", ctx)
    return render(request, "inventory/product_form.html", ctx)


@login_required
@role_required(CASHIER)
def stock_entry(request, pk):
    product = get_object_or_404(Product, pk=pk)
    form = StockEntryForm(request.POST or None, product=product)
    if form.is_valid():
        try:
            entry = form.save(commit=False)
            if entry.entry_type == StockEntry.EntryType.RESTOCK and form.cleaned_data.get("create_expense") and entry.total_cost > 0:
                expense = Expense.objects.create(
                    title=f"Stock purchase - {product.name}",
                    category=Expense.Category.INVENTORY,
                    amount=entry.total_cost,
                    expense_date=entry.date,
                    vendor=entry.supplier or product.supplier,
                    payment_method=Expense.PaymentMethod.CASH,
                    notes=entry.note or f"{entry.quantity} {product.unit} × UGX {entry.unit_cost:,.0f}",
                    recorded_by=request.user,
                )
                entry.related_expense = expense
            entry.save()
        except Exception:
            logger.exception("Stock entry failed for product id=%s", product.pk)
            form.add_error(None, "Stock entry could not be saved. Check quantity, type, and expense details.")
        else:
            if is_modal(request):
                return modal_success(f"Stock updated for {product.name}.")
            messages.success(request, f"Stock updated for {product.name}.")
            return redirect("inventory:list")
    history = product.stock_entries.select_related("related_expense").all()[:30]
    ctx = {"form": form, "product": product, "history": history}
    if is_modal(request):
        return render_modal(request, "inventory/stock_entry.html", ctx)
    return render(request, "inventory/stock_entry.html", ctx)


@login_required
@role_required(CASHIER)
def product_sale_list(request):
    today = timezone.localdate()
    start_date = request.GET.get("start_date") or today.replace(day=1).isoformat()
    end_date = request.GET.get("end_date") or today.isoformat()
    q = (request.GET.get("q") or "").strip()
    payment_method = request.GET.get("payment_method", "")

    qs = ProductSale.objects.select_related("product", "customer", "sold_by")
    if start_date:
        qs = qs.filter(sale_date__gte=start_date)
    if end_date:
        qs = qs.filter(sale_date__lte=end_date)
    if q:
        qs = qs.filter(Q(product__name__icontains=q) | Q(customer__name__icontains=q) | Q(notes__icontains=q))
    if payment_method:
        qs = qs.filter(payment_method=payment_method)

    page = Paginator(qs, 25).get_page(request.GET.get("page"))
    context = {
        "product_sales": page,
        "page_obj": page,
        "period_total": _money_total(qs, "total_amount"),
        "cash_total": _money_total(qs.filter(payment_method=ProductSale.PaymentMethod.CASH), "total_amount"),
        "mobile_money_total": _money_total(qs.filter(payment_method=ProductSale.PaymentMethod.MOBILE_MONEY), "total_amount"),
        "payment_method_choices": ProductSale.PaymentMethod.choices,
        "filter_payment_method": payment_method,
        "filter_q": q,
        "start_date": start_date,
        "end_date": end_date,
    }
    return render(request, "inventory/product_sales.html", context)


@login_required
@role_required(CASHIER)
def product_sale_create(request, pk=None):
    product = get_object_or_404(Product, pk=pk) if pk else None
    form = ProductSaleForm(request.POST or None, product=product)
    if form.is_valid():
        try:
            product_sale = form.save(commit=False)
            product_sale.sold_by = request.user
            product_sale.save()
            stock_entry = StockEntry.objects.create(
                product=product_sale.product,
                entry_type=StockEntry.EntryType.SOLD,
                quantity=-abs(product_sale.quantity),
                date=product_sale.sale_date,
                note=f"Product sale #{product_sale.pk}: {product_sale.quantity} × UGX {product_sale.unit_price:,.0f}",
            )
            product_sale.stock_entry = stock_entry
            product_sale.save(update_fields=["stock_entry", "total_amount", "updated_at"])
        except Exception:
            logger.exception("Product sale creation failed")
            form.add_error(None, "Product sale could not be saved. Check stock quantity and selling price.")
        else:
            if is_modal(request):
                return modal_success("Product sale recorded and stock reduced.")
            messages.success(request, "Product sale recorded and stock reduced.")
            return redirect("inventory:product_sales")
    ctx = {"form": form, "product": product, "title": "Record Product Sale"}
    if is_modal(request):
        return render_modal(request, "inventory/product_sale_form.html", ctx)
    return render(request, "inventory/product_sale_form.html", ctx)
