import logging

from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Count, Sum
from django.shortcuts import get_object_or_404, redirect, render

from apps.accounts.permissions import role_required
from apps.core.modal import is_modal, modal_success, render_modal

from .forms import CustomerForm
from .models import Customer

logger = logging.getLogger(__name__)


@login_required
@role_required("cashier")
def customer_list(request):
    qs = Customer.objects.all()
    paginator = Paginator(qs, 25)
    page = paginator.get_page(request.GET.get("page"))
    return render(request, "customers/list.html", {"customers": page, "page_obj": page})


@login_required
@role_required("cashier")
def customer_create(request):
    form = CustomerForm(request.POST or None)
    if form.is_valid():
        try:
            form.save()
        except Exception:
            logger.exception("Customer creation failed")
            form.add_error(None, "Customer could not be saved. Check the details and try again.")
        else:
            if is_modal(request):
                return modal_success("Customer saved successfully.")
            messages.success(request, "Customer saved successfully.")
            return redirect("customers:list")
    ctx = {"form": form, "title": "Add Customer"}
    if is_modal(request):
        return render_modal(request, "customers/form.html", ctx)
    return render(request, "customers/form.html", ctx)


@login_required
@role_required("cashier")
def customer_update(request, pk):
    customer = get_object_or_404(Customer, pk=pk)
    form = CustomerForm(request.POST or None, instance=customer)
    if form.is_valid():
        try:
            form.save()
        except Exception:
            logger.exception("Customer update failed for customer id=%s", customer.pk)
            form.add_error(None, "Customer could not be updated. Check the details and try again.")
        else:
            if is_modal(request):
                return modal_success(f"{customer} updated successfully.")
            messages.success(request, "Customer updated successfully.")
            return redirect("customers:list")
    ctx = {"form": form, "title": f"Edit {customer}"}
    if is_modal(request):
        return render_modal(request, "customers/form.html", ctx)
    return render(request, "customers/form.html", ctx)


@login_required
@role_required("cashier")
def customer_history(request, pk):
    customer = get_object_or_404(Customer, pk=pk)
    sales = customer.sales.select_related("employee", "service").prefetch_related("items__service", "items__employee").order_by("-created_at")
    totals = sales.aggregate(total_spend=Sum("amount"), visit_count=Count("id"))
    return render(request, "customers/history.html", {
        "customer": customer,
        "sales": sales,
        "total_spend": totals["total_spend"] or 0,
        "visit_count": totals["visit_count"] or 0,
    })
