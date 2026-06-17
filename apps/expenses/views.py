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

from .forms import ExpenseForm
from .models import Expense

ZERO = Value(0, output_field=DecimalField(max_digits=12, decimal_places=0))
logger = logging.getLogger(__name__)


def _parse_date(value, fallback=None):
    if not value:
        return fallback
    try:
        from datetime import datetime
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return fallback


def _expense_totals(qs):
    return qs.aggregate(total=Coalesce(Sum("amount"), ZERO))["total"] or Decimal("0")


@login_required
@role_required(CASHIER)
def expense_list(request):
    today = timezone.localdate()
    start_date = _parse_date(request.GET.get("start_date"), today.replace(day=1))
    end_date = _parse_date(request.GET.get("end_date"), today)
    category = request.GET.get("category", "")
    payment_method = request.GET.get("payment_method", "")
    q = (request.GET.get("q") or "").strip()

    qs = Expense.objects.select_related("recorded_by").all()
    if start_date:
        qs = qs.filter(expense_date__gte=start_date)
    if end_date:
        qs = qs.filter(expense_date__lte=end_date)
    if category:
        qs = qs.filter(category=category)
    if payment_method:
        qs = qs.filter(payment_method=payment_method)
    if q:
        qs = qs.filter(
            Q(title__icontains=q)
            | Q(vendor__icontains=q)
            | Q(receipt_number__icontains=q)
            | Q(notes__icontains=q)
        )

    paginator = Paginator(qs, 20)
    page = paginator.get_page(request.GET.get("page"))

    today_qs = Expense.objects.filter(expense_date=today)
    week_start = today - timedelta(days=today.weekday())
    month_start = today.replace(day=1)

    context = {
        "expenses": page,
        "page_obj": page,
        "start_date": start_date,
        "end_date": end_date,
        "filter_q": q,
        "filter_category": category,
        "filter_payment_method": payment_method,
        "category_choices": Expense.Category.choices,
        "payment_method_choices": Expense.PaymentMethod.choices,
        "period_total": _expense_totals(qs),
        "today_total": _expense_totals(today_qs),
        "week_total": _expense_totals(Expense.objects.filter(expense_date__gte=week_start, expense_date__lte=today)),
        "month_total": _expense_totals(Expense.objects.filter(expense_date__gte=month_start, expense_date__lte=today)),
    }
    return render(request, "expenses/list.html", context)


@login_required
@role_required(CASHIER)
def expense_create(request):
    form = ExpenseForm(request.POST or None)
    if form.is_valid():
        try:
            expense = form.save(commit=False)
            expense.recorded_by = request.user
            expense.save()
        except Exception:
            logger.exception("Expense creation failed")
            form.add_error(None, "Expense could not be saved. Check the details and try again.")
        else:
            if is_modal(request):
                return modal_success("Expense saved successfully.")
            messages.success(request, "Expense saved successfully.")
            return redirect("expenses:list")
    ctx = {"form": form, "title": "Add Expense", "is_create": True}
    if is_modal(request):
        return render_modal(request, "expenses/form.html", ctx)
    return render(request, "expenses/form.html", ctx)


@login_required
@role_required(CASHIER)
def expense_update(request, pk):
    expense = get_object_or_404(Expense, pk=pk)
    form = ExpenseForm(request.POST or None, instance=expense)
    if form.is_valid():
        try:
            form.save()
        except Exception:
            logger.exception("Expense update failed for expense id=%s", expense.pk)
            form.add_error(None, "Expense could not be updated. Check the details and try again.")
        else:
            if is_modal(request):
                return modal_success("Expense updated successfully.")
            messages.success(request, "Expense updated successfully.")
            return redirect("expenses:list")
    ctx = {"form": form, "title": f"Edit {expense.title}", "expense": expense, "is_create": False}
    if is_modal(request):
        return render_modal(request, "expenses/form.html", ctx)
    return render(request, "expenses/form.html", ctx)


@login_required
@role_required(CASHIER)
def expense_delete(request, pk):
    expense = get_object_or_404(Expense, pk=pk)
    if request.method == "POST":
        expense.delete()
        messages.success(request, "Expense deleted successfully.")
        return redirect("expenses:list")
    return render(request, "expenses/confirm_delete.html", {"expense": expense})
