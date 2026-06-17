import logging
from datetime import datetime, time, timedelta
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q, Sum
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from apps.accounts.permissions import CASHIER, has_any_role, is_employee_user, role_required
from apps.employees.models import Employee

from .forms import SaleForm
from .models import Sale

logger = logging.getLogger(__name__)


def day_bounds(target_date):
    current_tz = timezone.get_current_timezone()
    start = timezone.make_aware(datetime.combine(target_date, time.min), current_tz)
    end = start + timedelta(days=1)
    return start, end


def filter_datetime_day(queryset, target_date, field_prefix="created_at"):
    start, end = day_bounds(target_date)
    return queryset.filter(
        **{
            f"{field_prefix}__gte": start,
            f"{field_prefix}__lt": end,
        }
    )


def _employee_profile(request):
    return getattr(request.user, "employee_profile", None)


def _can_manage_sales(user):
    return has_any_role(user, CASHIER)


def _money_total(queryset, field_name):
    return queryset.aggregate(t=Sum(field_name))["t"] or Decimal("0")


@login_required
def sale_list(request):
    employee_profile = _employee_profile(request)
    can_manage = _can_manage_sales(request.user)
    is_employee_view = bool(
        employee_profile
        and is_employee_user(request.user)
        and not can_manage
        and not request.user.is_superuser
    )

    if not can_manage and not is_employee_view:
        messages.error(request, "You do not have permission to open that page.")
        return redirect("home")

    qs = (
        Sale.objects.select_related("employee", "service", "customer")
        .prefetch_related("items__service", "items__employee", "items__support_employee")
        .order_by("-created_at", "-id")
    )
    today = timezone.localdate()

    if is_employee_view:
        qs = qs.filter(Q(items__employee=employee_profile) | Q(items__support_employee=employee_profile)).distinct()
    else:
        status_filter = request.GET.get("status", "")
        if status_filter:
            qs = qs.filter(status=status_filter)

        payment_method = request.GET.get("payment_method", "")
        if payment_method:
            qs = qs.filter(payment_method=payment_method)

    date_str = request.GET.get("date", "")
    employee_id = request.GET.get("employee", "")

    if date_str:
        try:
            filter_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            qs = filter_datetime_day(qs, filter_date)
        except ValueError:
            pass

    if employee_id and can_manage:
        qs = qs.filter(Q(items__employee_id=employee_id) | Q(items__support_employee_id=employee_id)).distinct()

    todays_qs = Sale.objects.filter(status=Sale.Status.APPROVED)
    todays_qs = filter_datetime_day(todays_qs, today)
    if is_employee_view:
        todays_qs = todays_qs.filter(Q(items__employee=employee_profile) | Q(items__support_employee=employee_profile)).distinct()

    today_total = _money_total(todays_qs, "amount")
    today_commission = _money_total(todays_qs, "commission_amount")
    today_cash = _money_total(todays_qs.filter(payment_method=Sale.PaymentMethod.CASH), "amount")
    today_mobile_money = _money_total(todays_qs.filter(payment_method=Sale.PaymentMethod.MOBILE_MONEY), "amount")

    pending_qs = Sale.objects.filter(status=Sale.Status.PENDING)
    if is_employee_view:
        pending_qs = pending_qs.filter(Q(items__employee=employee_profile) | Q(items__support_employee=employee_profile)).distinct()
    pending_count = pending_qs.count()

    paginator = Paginator(qs, 25)
    page = paginator.get_page(request.GET.get("page"))

    context = {
        "sales": page,
        "page_obj": page,
        "today_total": today_total,
        "today_commission": today_commission,
        "today_cash": today_cash,
        "today_mobile_money": today_mobile_money,
        "pending_count": pending_count,
        "employees": Employee.objects.filter(is_active=True).order_by("name"),
        "filter_date": date_str,
        "filter_employee": employee_id if can_manage else "",
        "filter_status": request.GET.get("status", "") if can_manage else "",
        "filter_payment_method": request.GET.get("payment_method", "") if can_manage else "",
        "status_choices": Sale.Status.choices,
        "payment_method_choices": Sale.PaymentMethod.choices,
        "can_manage_sales": can_manage,
        "is_employee_view": is_employee_view,
    }
    return render(request, "sales/list.html", context)


@login_required
def create_sale(request):
    employee_profile = _employee_profile(request)
    can_manage = _can_manage_sales(request.user)
    employee_can_submit = bool(employee_profile and is_employee_user(request.user))
    if not can_manage and not employee_can_submit:
        messages.error(request, "You do not have permission to submit services.")
        return redirect("home")

    form = SaleForm(request.POST or None, current_user=request.user)
    if form.is_valid():
        try:
            sale = form.save()
        except Exception as exc:
            logger.exception("Sale creation failed")
            form.add_error(None, f"Sale could not be saved. Check selected services, employees, amount, payment method and support employee. Technical reason: {type(exc).__name__}: {exc}")
        else:
            if sale.status == Sale.Status.PENDING:
                messages.success(request, "Service submitted for admin/cashier approval.")
                success_msg = "Service submitted for approval."
            else:
                messages.success(request, "Sale recorded and approved successfully.")
                success_msg = "Sale recorded successfully."
            if request.headers.get("X-Modal"):
                response = HttpResponse("")
                response["X-Modal-Success"] = success_msg
                return response
            return redirect("sales:list")

    available_services = list(form.fields["services"].queryset)
    selected_service_ids = {str(value) for value in (form["services"].value() or [])}
    is_employee_submission = form.is_employee_submission
    return render(request, "sales/form.html", {
        "form": form,
        "available_services": available_services,
        "selected_service_ids": selected_service_ids,
        "employees": Employee.objects.filter(is_active=True).order_by("name") if not is_employee_submission else [],
        "existing_items": [],
        "is_create": True,
        "is_employee_submission": is_employee_submission,
    })


@login_required
def pending_approvals_status(request):
    if not _can_manage_sales(request.user):
        return JsonResponse({"count": 0, "latest_id": ""})
    qs = Sale.objects.filter(status=Sale.Status.PENDING).order_by("-created_at", "-id")
    latest = qs.first()
    count = qs.count()
    return JsonResponse({
        "count": count,
        "latest_id": latest.pk if latest else "",
        "message": f"{count} sale{'s' if count != 1 else ''} pending approval",
    })


@login_required
@role_required(CASHIER)
def edit_sale(request, pk):
    sale = get_object_or_404(Sale, pk=pk)
    form = SaleForm(request.POST or None, instance=sale, current_user=request.user)
    if form.is_valid():
        try:
            form.save()
        except Exception as exc:
            logger.exception("Sale update failed for sale id=%s", sale.pk)
            form.add_error(None, f"Sale could not be updated. Check selected services, employees, amount, payment method and support employee. Technical reason: {type(exc).__name__}: {exc}")
        else:
            messages.success(request, "Sale updated successfully.")
            if request.headers.get("X-Modal"):
                response = HttpResponse("")
                response["X-Modal-Success"] = "Sale updated successfully."
                return response
            return redirect("sales:list")

    available_services = list(form.fields["services"].queryset)
    selected_service_ids = {str(sid) for sid in sale.items.values_list("service_id", flat=True)}
    if form.is_bound:
        selected_service_ids = {str(value) for value in (form["services"].value() or [])}
    return render(request, "sales/form.html", {
        "form": form,
        "available_services": available_services,
        "selected_service_ids": selected_service_ids,
        "employees": Employee.objects.filter(is_active=True).order_by("name"),
        "existing_items": sale.items.select_related("service", "employee", "support_employee"),
        "sale": sale,
        "is_create": False,
        "is_employee_submission": False,
    })


@login_required
@role_required(CASHIER)
def approve_sale(request, pk):
    sale = get_object_or_404(Sale.objects.prefetch_related("items"), pk=pk)
    if request.method == "POST":
        payment_method = request.POST.get("payment_method") or Sale.PaymentMethod.CASH
        support_assignments = {}
        for item in sale.items.all():
            support_assignments[str(item.pk)] = request.POST.get(f"support_employee_for_item_{item.pk}") or ""
        sale.approve(request.user, payment_method=payment_method, support_assignments=support_assignments)
        messages.success(request, "Service approved. Payment method and support commission have now been counted.")
    return redirect("sales:list")


@login_required
@role_required(CASHIER)
def reject_sale(request, pk):
    sale = get_object_or_404(Sale, pk=pk)
    if request.method == "POST":
        sale.reject(request.user)
        messages.success(request, "Service rejected. No commission was counted.")
    return redirect("sales:list")


@login_required
@role_required(CASHIER)
def delete_sale(request, pk):
    sale = get_object_or_404(Sale, pk=pk)
    if request.method == "POST":
        sale.status = Sale.Status.CANCELLED
        sale.commission_amount = 0
        sale.save(update_fields=["status", "commission_amount"])
        sale.items.update(commission_amount=0, support_commission_amount=0)
        messages.success(request, "Sale cancelled successfully.")
        if request.headers.get("X-Modal"):
            response = HttpResponse("")
            response["X-Modal-Success"] = "Sale cancelled successfully."
            return response
        return redirect("sales:list")
    if request.headers.get("X-Modal"):
        return render(request, "sales/confirm_delete.html", {"sale": sale})
    return render(request, "sales/confirm_delete.html", {"sale": sale})
