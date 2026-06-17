import logging
from datetime import timedelta
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Count, DecimalField, Q, Sum, Value
from django.db.models.functions import Coalesce
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from apps.accounts.permissions import role_required
from apps.sales.models import Sale, SaleItem

from .forms import EmployeeForm
from .models import Department, Employee, Role

ZERO = Value(0, output_field=DecimalField(max_digits=12, decimal_places=0))
logger = logging.getLogger(__name__)


def _employee_save_error_message(action, exc):
    technical = f" Technical reason: {exc.__class__.__name__}: {exc}"
    if "Permission denied" in str(exc) or exc.__class__.__name__ == "PermissionError":
        return (
            f"Employee could not be {action}. The uploaded photo could not be written to the media folder."
            " Please check that media/employees/photos exists and is writable on the server."
            + technical
        )
    return (
        f"Employee could not be {action}. Please check role, department, services, ID number, and photo."
        + technical
    )


def _money_total(qs, field):
    return qs.aggregate(total=Coalesce(Sum(field), ZERO))["total"] or Decimal("0")


def _filtered_employee_queryset(request):
    qs = Employee.objects.select_related("user", "role", "department").prefetch_related("services").all()
    q = (request.GET.get("q") or "").strip()
    role = request.GET.get("role", "")
    department = request.GET.get("department", "")
    status = request.GET.get("status", "")
    id_type = request.GET.get("id_type", "")

    if q:
        qs = qs.filter(
            Q(name__icontains=q)
            | Q(phone__icontains=q)
            | Q(id_number__icontains=q)
            | Q(national_id__icontains=q)
            | Q(user__username__icontains=q)
            | Q(department__name__icontains=q)
            | Q(role__name__icontains=q)
            | Q(services__name__icontains=q)
        ).distinct()
    if role:
        qs = qs.filter(role_id=role)
    if department:
        qs = qs.filter(department_id=department)
    if status == "active":
        qs = qs.filter(is_active=True)
    elif status == "inactive":
        qs = qs.filter(is_active=False)
    elif status == "password":
        qs = qs.filter(must_change_password=True)
    if id_type:
        qs = qs.filter(id_type=id_type)
    return qs, {"q": q, "role": role, "department": department, "status": status, "id_type": id_type}


@login_required
@role_required("admin")
def employee_list(request):
    qs, filters = _filtered_employee_queryset(request)
    today = timezone.localdate()
    month_start = today.replace(day=1)

    summary = {
        "total": qs.count(),
        "active": qs.filter(is_active=True).count(),
        "must_change_password": qs.filter(must_change_password=True).count(),
        "departments": qs.exclude(department__isnull=True).values("department_id").distinct().count(),
    }

    paginator = Paginator(qs, 18)
    page = paginator.get_page(request.GET.get("page"))

    # Small performance snapshot for the cards. Approved items only count in commission.
    employees_on_page = list(page.object_list)
    for employee in employees_on_page:
        approved_items = SaleItem.objects.filter(
            employee=employee,
            sale__status=Sale.Status.APPROVED,
            sale__created_at__date__gte=month_start,
            sale__created_at__date__lte=today,
        )
        employee.month_jobs = approved_items.count()
        employee.month_sales = _money_total(approved_items, "price")
        employee.month_commission = _money_total(approved_items, "commission_amount")
        employee.assigned_service_count = employee.services.count() or (1 if employee.service_id else 0)
        employee.preview_services = list(employee.allowed_services()[:3])

    context = {
        "employees": employees_on_page,
        "page_obj": page,
        "filters": filters,
        "roles": Role.objects.all(),
        "departments": Department.objects.filter(is_active=True),
        "id_type_choices": Employee.IdentificationType.choices,
        "summary": summary,
    }
    return render(request, "employees/list.html", context)


from apps.core.modal import is_modal, modal_success, render_modal


@login_required
@role_required("admin")
def employee_create(request):
    form = EmployeeForm(request.POST or None, request.FILES or None)
    if form.is_valid():
        try:
            with transaction.atomic():
                form.save()
        except Exception as exc:
            logger.exception("Employee creation failed")
            detail = f" Details: {exc}" if settings.DEBUG else ""
            form.add_error(None, _employee_save_error_message("saved", exc))
        else:
            if is_modal(request):
                return modal_success("Employee saved successfully.")
            messages.success(request, "Employee saved successfully.")
            return redirect("employees:list")
    ctx = {"form": form, "title": "Add Employee", "employee": form.instance, "is_create": True}
    if is_modal(request):
        return render_modal(request, "employees/form.html", ctx)
    return render(request, "employees/form.html", ctx)


@login_required
@role_required("admin")
def employee_detail(request, pk):
    employee = get_object_or_404(
        Employee.objects.select_related("user", "role", "department").prefetch_related("services"),
        pk=pk,
    )
    today = timezone.localdate()
    month_start = today.replace(day=1)

    items = SaleItem.objects.select_related("sale", "sale__customer", "service").filter(employee=employee)
    approved_items = items.filter(sale__status=Sale.Status.APPROVED)
    month_items = approved_items.filter(sale__created_at__date__gte=month_start, sale__created_at__date__lte=today)
    today_items = approved_items.filter(sale__created_at__date=today)

    service_breakdown = (
        approved_items.values("service__name")
        .annotate(
            jobs=Count("id"),
            total_sales=Coalesce(Sum("price"), ZERO),
            total_commission=Coalesce(Sum("commission_amount"), ZERO),
        )
        .order_by("-total_sales", "service__name")[:12]
    )

    context = {
        "employee": employee,
        "assigned_services": employee.allowed_services(),
        "recent_items": items.order_by("-sale__created_at", "-id")[:20],
        "service_breakdown": service_breakdown,
        "today_jobs": today_items.count(),
        "today_sales": _money_total(today_items, "price"),
        "today_commission": _money_total(today_items, "commission_amount"),
        "month_jobs": month_items.count(),
        "month_sales": _money_total(month_items, "price"),
        "month_commission": _money_total(month_items, "commission_amount"),
        "all_jobs": approved_items.count(),
        "all_sales": _money_total(approved_items, "price"),
        "all_commission": _money_total(approved_items, "commission_amount"),
        "pending_count": items.filter(sale__status=Sale.Status.PENDING).count(),
        "rejected_count": items.filter(sale__status=Sale.Status.REJECTED).count(),
        "month_start": month_start,
        "today": today,
    }
    return render(request, "employees/detail.html", context)


@login_required
@role_required("admin")
def employee_update(request, pk):
    employee = get_object_or_404(Employee, pk=pk)
    form = EmployeeForm(request.POST or None, request.FILES or None, instance=employee)
    if form.is_valid():
        try:
            with transaction.atomic():
                form.save()
        except Exception as exc:
            logger.exception("Employee update failed for employee id=%s", employee.pk)
            detail = f" Details: {exc}" if settings.DEBUG else ""
            form.add_error(None, _employee_save_error_message("updated", exc))
        else:
            if is_modal(request):
                return modal_success(f"{employee.name} updated successfully.")
            messages.success(request, "Employee updated successfully.")
            return redirect("employees:detail", pk=employee.pk)
    ctx = {"form": form, "title": f"Edit {employee.name}", "employee": employee, "is_create": False}
    if is_modal(request):
        return render_modal(request, "employees/form.html", ctx)
    return render(request, "employees/form.html", ctx)
