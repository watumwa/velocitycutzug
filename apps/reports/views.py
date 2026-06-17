import csv
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count, DecimalField, Q, Sum, Value
from django.db.models.functions import Coalesce
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.utils import timezone

from apps.accounts.permissions import CASHIER, is_employee_user, role_required
from apps.sales.models import Sale, SaleItem

from .services import (
    apply_date_range,
    filter_datetime_day,
    get_daily_report,
    get_dashboard_metrics,
    get_employee_report,
    get_service_report,
    parse_date,
)

ZERO = Value(0, output_field=DecimalField(max_digits=12, decimal_places=0))


def _employee_profile(request):
    return getattr(request.user, "employee_profile", None)


def _date_range_from_request(request):
    today = timezone.localdate()
    start_date = parse_date(request.GET.get("start_date"), today.replace(day=1))
    end_date = parse_date(request.GET.get("end_date"), today)
    return start_date, end_date


def _my_commission_context(employee, start_date=None, end_date=None):
    today = timezone.localdate()
    start_date = start_date or today.replace(day=1)
    end_date = end_date or today

    items = SaleItem.objects.select_related("sale", "service", "sale__customer", "employee", "support_employee").filter(
        Q(employee=employee) | Q(support_employee=employee)
    )
    items = apply_date_range(items, start_date, end_date, field_prefix="sale__created_at")
    approved_items = items.filter(sale__status=Sale.Status.APPROVED)

    today_items = filter_datetime_day(
        SaleItem.objects.select_related("sale", "service", "sale__customer", "employee", "support_employee").filter(
            Q(employee=employee) | Q(support_employee=employee)
        ),
        today,
        field_prefix="sale__created_at",
    )
    today_approved_items = today_items.filter(sale__status=Sale.Status.APPROVED)

    def build_totals(queryset):
        jobs = 0
        support_jobs = 0
        sales = Decimal("0")
        commission = Decimal("0")
        records = []
        service_map = {}

        for item in queryset:
            is_main = item.employee_id == employee.pk
            is_support = item.support_employee_id == employee.pk
            if not is_main and not is_support:
                continue

            if is_main:
                jobs += 1
                sales += item.price or Decimal("0")
                earned = item.commission_amount or Decimal("0")
                role = "Main"
            else:
                support_jobs += 1
                earned = item.support_commission_amount or Decimal("0")
                role = "Support"

            commission += earned
            row = service_map.setdefault(item.service_id, {
                "service__name": item.service.name,
                "jobs": 0,
                "support_jobs": 0,
                "total_sales": Decimal("0"),
                "total_commission": Decimal("0"),
                "main_commission": Decimal("0"),
                "support_commission": Decimal("0"),
            })
            if is_main:
                row["jobs"] += 1
                row["total_sales"] += item.price or Decimal("0")
                row["main_commission"] += earned
            else:
                row["support_jobs"] += 1
                row["support_commission"] += earned
            row["total_commission"] += earned

            records.append({
                "date": item.sale.created_at,
                "service": item.service.name,
                "customer": item.sale.customer or "Walk-in",
                "sale_amount": item.price,
                "commission": earned,
                "rate": item.commission_rate if is_main else None,
                "role": role,
                "status": item.sale.status,
                "status_display": item.sale.get_status_display(),
            })

        breakdown = sorted(service_map.values(), key=lambda r: (-r["total_commission"], r["service__name"]))
        return {
            "jobs": jobs,
            "support_jobs": support_jobs,
            "total_jobs": jobs + support_jobs,
            "sales": sales,
            "commission": commission,
            "records": sorted(records, key=lambda r: r["date"], reverse=True),
            "breakdown": breakdown,
        }

    totals = build_totals(approved_items)
    today_totals = build_totals(today_approved_items)

    return {
        "employee": employee,
        "start_date": start_date,
        "end_date": end_date,
        "items": totals["records"],
        "service_breakdown": totals["breakdown"],
        "jobs_done": totals["jobs"],
        "support_jobs_done": totals["support_jobs"],
        "total_jobs_done": totals["total_jobs"],
        "total_sales": totals["sales"],
        "total_commission": totals["commission"],
        "net_revenue": totals["sales"] - totals["commission"],
        "today_jobs_done": today_totals["jobs"],
        "today_support_jobs_done": today_totals["support_jobs"],
        "today_total_jobs_done": today_totals["total_jobs"],
        "today_total_sales": today_totals["sales"],
        "today_total_commission": today_totals["commission"],
        "pending_count": items.filter(sale__status=Sale.Status.PENDING).count(),
        "rejected_count": items.filter(sale__status=Sale.Status.REJECTED).count(),
        "today_pending_count": today_items.filter(sale__status=Sale.Status.PENDING).count(),
    }

@login_required
def dashboard(request):
    employee = _employee_profile(request)
    if employee and is_employee_user(request.user) and not request.user.is_superuser:
        context = _my_commission_context(employee)
        context["today"] = timezone.localdate()
        return render(request, "reports/my_commissions.html", context)
    return render(request, "reports/dashboard.html", get_dashboard_metrics())


@login_required
@role_required(CASHIER)
def daily_summary(request):
    target_date = parse_date(request.GET.get("date"), timezone.localdate())
    context = get_daily_report(target_date)

    if request.GET.get("export") == "csv":
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = f'attachment; filename="daily-{target_date}.csv"'
        writer = csv.writer(response)
        writer.writerow(["Time", "Type", "Employee / Cashier", "Item", "Customer", "Payment", "Amount", "Commission"])
        for sale in context["sales"]:
            writer.writerow([
                sale.created_at.strftime("%H:%M"),
                "Service",
                sale.employee_summary,
                sale.service_summary,
                str(sale.customer or "Walk-in"),
                sale.get_payment_method_display(),
                sale.amount,
                sale.commission_amount,
            ])
        for product_sale in context.get("product_sales", []):
            writer.writerow([
                product_sale.created_at.strftime("%H:%M"),
                "Product",
                product_sale.sold_by.get_full_name() or product_sale.sold_by.username if product_sale.sold_by else "-",
                product_sale.product.name,
                str(product_sale.customer or "Walk-in"),
                product_sale.get_payment_method_display(),
                product_sale.total_amount,
                0,
            ])
        return response

    return render(request, "reports/daily_summary.html", context)


@login_required
@role_required(CASHIER)
def employee_report(request):
    start_date, end_date = _date_range_from_request(request)
    rows = get_employee_report(start_date, end_date)

    if request.GET.get("export") == "csv":
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = f'attachment; filename="employee-report-{start_date}-{end_date}.csv"'
        writer = csv.writer(response)
        writer.writerow(["Employee", "Main Jobs", "Support Jobs", "Total Jobs", "Total Sales", "Main Commission", "Support Commission", "Total Commission", "Net Revenue"])
        for row in rows:
            writer.writerow([row["employee_name"], row["jobs_done"], row["support_jobs_done"], row["total_jobs"], row["total_sales"], row["main_commission"], row["support_commission"], row["total_commission"], row["net_revenue"]])
        return response

    context = {"rows": rows, "start_date": start_date, "end_date": end_date}
    return render(request, "reports/employee_report.html", context)


@login_required
@role_required(CASHIER)
def service_report(request):
    start_date, end_date = _date_range_from_request(request)
    rows = get_service_report(start_date, end_date)

    if request.GET.get("export") == "csv":
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = f'attachment; filename="service-report-{start_date}-{end_date}.csv"'
        writer = csv.writer(response)
        writer.writerow(["Service", "Jobs Done", "Total Revenue"])
        for row in rows:
            writer.writerow([row["service__name"], row["jobs_done"], row["total_revenue"]])
        return response

    context = {"rows": rows, "start_date": start_date, "end_date": end_date}
    return render(request, "reports/service_report.html", context)


@login_required
def my_commissions(request):
    employee = _employee_profile(request)
    if not employee:
        messages.error(request, "Your login is not linked to an employee profile.")
        return redirect("home")
    start_date, end_date = _date_range_from_request(request)
    context = _my_commission_context(employee, start_date, end_date)

    if request.GET.get("export") == "csv":
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = f'attachment; filename="my-commissions-{start_date}-{end_date}.csv"'
        writer = csv.writer(response)
        writer.writerow(["Date", "Service", "Customer", "Role", "Sale Amount", "Commission", "Rate", "Status"])
        for item in context["items"]:
            writer.writerow([
                item["date"].strftime("%Y-%m-%d %H:%M"),
                item["service"],
                str(item["customer"]),
                item["role"],
                item["sale_amount"],
                item["commission"],
                "Fixed support" if item["role"] == "Support" else (item["rate"] or "Default"),
                item["status_display"],
            ])
        return response

    return render(request, "reports/my_commissions.html", context)
