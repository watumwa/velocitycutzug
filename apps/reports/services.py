from decimal import Decimal
from types import SimpleNamespace
from datetime import date, datetime, time, timedelta

from django.db.models import Count, DecimalField, Sum, Value
from django.db.models.functions import Coalesce
from django.utils import timezone

from apps.customers.models import Customer
from apps.sales.models import Sale, SaleItem
from apps.sales.services import allocate_item_commissions

ZERO = Value(0, output_field=DecimalField(max_digits=12, decimal_places=0))
DECIMAL_ZERO = Decimal("0")


def expense_queryset():
    from apps.expenses.models import Expense
    return Expense.objects.all()


def product_sale_queryset():
    from apps.inventory.models import ProductSale
    return ProductSale.objects.select_related("product", "customer", "sold_by")


def aggregate_expenses(start_date=None, end_date=None):
    expenses = expense_queryset()
    if start_date:
        expenses = expenses.filter(expense_date__gte=start_date)
    if end_date:
        expenses = expenses.filter(expense_date__lte=end_date)
    return aggregate_money(expenses, "amount")


def aggregate_product_sales(start_date=None, end_date=None):
    product_sales = product_sale_queryset()
    if start_date:
        product_sales = product_sales.filter(sale_date__gte=start_date)
    if end_date:
        product_sales = product_sales.filter(sale_date__lte=end_date)
    return aggregate_money(product_sales, "total_amount")


def parse_date(value, fallback=None):
    if not value:
        return fallback
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return fallback


def day_bounds(target_date):
    """
    Return timezone-aware start and end datetime for a given local date.

    This avoids created_at__date filters, which can fail on MySQL/MariaDB
    production hosting when timezone tables are not fully available.
    """
    current_tz = timezone.get_current_timezone()
    start = timezone.make_aware(datetime.combine(target_date, time.min), current_tz)
    end = start + timedelta(days=1)
    return start, end


def filter_datetime_day(queryset, target_date, field_prefix="created_at"):
    """
    Filter a DateTimeField for one local day using >= start and < end.
    """
    start, end = day_bounds(target_date)
    return queryset.filter(
        **{
            f"{field_prefix}__gte": start,
            f"{field_prefix}__lt": end,
        }
    )


def apply_date_range(queryset, start_date=None, end_date=None, field_prefix="created_at"):
    """
    Filter DateTimeFields using datetime ranges instead of __date lookups.
    """
    if start_date:
        start, _ = day_bounds(start_date)
        queryset = queryset.filter(**{f"{field_prefix}__gte": start})
    if end_date:
        _, end = day_bounds(end_date)
        queryset = queryset.filter(**{f"{field_prefix}__lt": end})
    return queryset


def aggregate_money(queryset, field_name):
    return queryset.aggregate(total=Coalesce(Sum(field_name), ZERO))["total"] or DECIMAL_ZERO


def percent_of(part, whole):
    part = part or DECIMAL_ZERO
    whole = whole or DECIMAL_ZERO
    if whole == DECIMAL_ZERO:
        return DECIMAL_ZERO
    value = ((part / whole) * Decimal("100")).quantize(Decimal("1"))
    return max(DECIMAL_ZERO, min(Decimal("100"), value))


def percentage_growth(current, previous):
    current = current or DECIMAL_ZERO
    previous = previous or DECIMAL_ZERO
    if previous == DECIMAL_ZERO:
        return None
    return ((current - previous) / previous * Decimal("100")).quantize(Decimal("0.1"))


def growth_label(value):
    if value is None:
        return "No baseline"
    prefix = "+" if value > DECIMAL_ZERO else ""
    return f"{prefix}{value}%"


def growth_direction(value):
    if value is None or value == DECIMAL_ZERO:
        return "neutral"
    return "up" if value > DECIMAL_ZERO else "down"


def sale_queryset():
    return (
        Sale.objects.filter(status=Sale.Status.APPROVED)
        .select_related("employee", "service", "customer")
        .prefetch_related("items__service", "items__employee", "items__support_employee")
    )


def get_sale_item_commissions(sale):
    items = sale.sale_items
    if items:
        return allocate_item_commissions(items, sale.commission_amount)
    if sale.service_id:
        fallback_item = SimpleNamespace(service=sale.service, price=sale.amount or Decimal("0"))
        return allocate_item_commissions([fallback_item], sale.commission_amount)
    return []


def get_dashboard_metrics():
    today = timezone.localdate()
    start_of_week = today - timedelta(days=today.weekday())
    start_of_month = today.replace(day=1)
    yesterday = today - timedelta(days=1)
    previous_week_start = start_of_week - timedelta(days=7)
    previous_week_end = start_of_week - timedelta(days=1)
    previous_month_end = start_of_month - timedelta(days=1)
    previous_month_start = previous_month_end.replace(day=1)

    sales = sale_queryset()
    product_sales = product_sale_queryset()
    sale_items = SaleItem.objects.filter(
        sale__status=Sale.Status.APPROVED
    ).select_related("service", "sale", "employee", "support_employee")

    today_sales = filter_datetime_day(sales, today)
    yesterday_sales = filter_datetime_day(sales, yesterday)
    week_sales = apply_date_range(sales, start_of_week, today)
    previous_week_sales = apply_date_range(sales, previous_week_start, previous_week_end)
    month_sales = apply_date_range(sales, start_of_month, today)
    previous_month_sales = apply_date_range(sales, previous_month_start, previous_month_end)

    today_product_sales = product_sales.filter(sale_date=today)
    yesterday_product_sales = product_sales.filter(sale_date=yesterday)
    week_product_sales = product_sales.filter(sale_date__gte=start_of_week, sale_date__lte=today)
    previous_week_product_sales = product_sales.filter(
        sale_date__range=(previous_week_start, previous_week_end)
    )
    month_product_sales = product_sales.filter(sale_date__gte=start_of_month, sale_date__lte=today)
    previous_month_product_sales = product_sales.filter(
        sale_date__range=(previous_month_start, previous_month_end)
    )

    month_items = apply_date_range(
        sale_items,
        start_of_month,
        today,
        field_prefix="sale__created_at",
    )

    today_service_revenue = aggregate_money(today_sales, "amount")
    today_product_revenue = aggregate_money(today_product_sales, "total_amount")
    today_revenue = today_service_revenue + today_product_revenue
    today_commission = aggregate_money(today_sales, "commission_amount")
    today_cash_revenue = aggregate_money(today_sales.filter(payment_method=Sale.PaymentMethod.CASH), "amount") + aggregate_money(today_product_sales.filter(payment_method="cash"), "total_amount")
    today_mobile_money_revenue = aggregate_money(today_sales.filter(payment_method=Sale.PaymentMethod.MOBILE_MONEY), "amount") + aggregate_money(today_product_sales.filter(payment_method="mobile_money"), "total_amount")
    today_support_commission = aggregate_money(today_sales, "items__support_commission_amount")
    today_expenses = aggregate_expenses(today, today)

    week_service_revenue = aggregate_money(week_sales, "amount")
    week_product_revenue = aggregate_money(week_product_sales, "total_amount")
    week_revenue = week_service_revenue + week_product_revenue
    week_commission = aggregate_money(week_sales, "commission_amount")
    week_cash_revenue = aggregate_money(week_sales.filter(payment_method=Sale.PaymentMethod.CASH), "amount") + aggregate_money(week_product_sales.filter(payment_method="cash"), "total_amount")
    week_mobile_money_revenue = aggregate_money(week_sales.filter(payment_method=Sale.PaymentMethod.MOBILE_MONEY), "amount") + aggregate_money(week_product_sales.filter(payment_method="mobile_money"), "total_amount")
    week_expenses = aggregate_expenses(start_of_week, today)

    month_service_revenue = aggregate_money(month_sales, "amount")
    month_product_revenue = aggregate_money(month_product_sales, "total_amount")
    month_revenue = month_service_revenue + month_product_revenue
    month_commission = aggregate_money(month_sales, "commission_amount")
    month_cash_revenue = aggregate_money(month_sales.filter(payment_method=Sale.PaymentMethod.CASH), "amount") + aggregate_money(month_product_sales.filter(payment_method="cash"), "total_amount")
    month_mobile_money_revenue = aggregate_money(month_sales.filter(payment_method=Sale.PaymentMethod.MOBILE_MONEY), "amount") + aggregate_money(month_product_sales.filter(payment_method="mobile_money"), "total_amount")
    month_expenses = aggregate_expenses(start_of_month, today)

    yesterday_revenue = aggregate_money(yesterday_sales, "amount") + aggregate_money(
        yesterday_product_sales, "total_amount"
    )
    previous_week_revenue = aggregate_money(previous_week_sales, "amount") + aggregate_money(
        previous_week_product_sales, "total_amount"
    )
    previous_month_revenue = aggregate_money(previous_month_sales, "amount") + aggregate_money(
        previous_month_product_sales, "total_amount"
    )

    top_employee = (
        month_items.filter(employee__isnull=False)
        .values("employee__name")
        .annotate(
            jobs_done=Count("id"),
            total_sales=Coalesce(Sum("price"), ZERO),
            total_commission=Coalesce(Sum("commission_amount"), ZERO),
        )
        .order_by("-total_sales", "-jobs_done", "employee__name")
        .first()
    )

    top_service = (
        month_items.values("service__name")
        .annotate(
            jobs_done=Count("id"),
            total_sales=Coalesce(Sum("price"), ZERO),
        )
        .order_by("-jobs_done", "-total_sales", "service__name")
        .first()
    )

    today_net_revenue = today_revenue - today_commission - today_expenses
    week_net_revenue = week_revenue - week_commission - week_expenses
    month_net_revenue = month_revenue - month_commission - month_expenses

    today_growth = percentage_growth(today_revenue, yesterday_revenue)
    week_growth = percentage_growth(week_revenue, previous_week_revenue)
    month_growth = percentage_growth(month_revenue, previous_month_revenue)

    top_employee_sales = top_employee["total_sales"] if top_employee else DECIMAL_ZERO
    top_service_sales = top_service["total_sales"] if top_service else DECIMAL_ZERO

    today_transaction_count = today_sales.count() + today_product_sales.count()
    today_walk_in_count = today_sales.filter(customer__isnull=True).count() + today_product_sales.filter(
        customer__isnull=True
    ).count()

    from apps.inventory.models import Product

    inventory_alert_count = sum(1 for p in Product.objects.all() if p.is_low_stock)

    return {
        "today": today,
        "today_revenue": today_revenue,
        "today_service_revenue": today_service_revenue,
        "today_product_revenue": today_product_revenue,
        "today_commission": today_commission,
        "today_support_commission": today_support_commission,
        "today_cash_revenue": today_cash_revenue,
        "today_mobile_money_revenue": today_mobile_money_revenue,
        "today_expenses": today_expenses,
        "today_net_revenue": today_net_revenue,
        "today_net_margin": percent_of(today_net_revenue, today_revenue),
        "today_transaction_count": today_transaction_count,
        "today_walk_in_count": today_walk_in_count,
        "today_appointments_count": 0,
        "products_sold_count": sum((sale.quantity for sale in today_product_sales), 0),
        "inventory_alert_count": inventory_alert_count,
        "upcoming_appointments": [],
        "today_growth": today_growth,
        "today_growth_label": growth_label(today_growth),
        "today_growth_direction": growth_direction(today_growth),
        "week_revenue": week_revenue,
        "week_service_revenue": week_service_revenue,
        "week_product_revenue": week_product_revenue,
        "week_net_revenue": week_net_revenue,
        "week_expenses": week_expenses,
        "week_cash_revenue": week_cash_revenue,
        "week_mobile_money_revenue": week_mobile_money_revenue,
        "week_net_margin": percent_of(week_net_revenue, week_revenue),
        "week_growth": week_growth,
        "week_growth_label": growth_label(week_growth),
        "week_growth_direction": growth_direction(week_growth),
        "month_revenue": month_revenue,
        "month_service_revenue": month_service_revenue,
        "month_product_revenue": month_product_revenue,
        "month_net_revenue": month_net_revenue,
        "month_expenses": month_expenses,
        "month_cash_revenue": month_cash_revenue,
        "month_mobile_money_revenue": month_mobile_money_revenue,
        "month_net_margin": percent_of(month_net_revenue, month_revenue),
        "month_growth": month_growth,
        "month_growth_label": growth_label(month_growth),
        "month_growth_direction": growth_direction(month_growth),
        "transaction_count": sales.count() + product_sales.count(),
        "customer_count": Customer.objects.count(),
        "top_employee": top_employee,
        "top_employee_share": percent_of(top_employee_sales, month_service_revenue),
        "top_service": top_service,
        "top_service_share": percent_of(top_service_sales, month_service_revenue),
        "recent_sales": sales[:10],
        "recent_product_sales": product_sales[:6],
    }


def get_daily_report(target_date: date):
    sales = filter_datetime_day(sale_queryset(), target_date)
    product_sales = product_sale_queryset().filter(sale_date=target_date)

    service_sales_total = aggregate_money(sales, "amount")
    product_sales_total = aggregate_money(product_sales, "total_amount")
    total_sales = service_sales_total + product_sales_total
    total_commission = aggregate_money(sales, "commission_amount")
    total_support_commission = aggregate_money(sales, "items__support_commission_amount")
    cash_total = aggregate_money(sales.filter(payment_method=Sale.PaymentMethod.CASH), "amount") + aggregate_money(product_sales.filter(payment_method="cash"), "total_amount")
    mobile_money_total = aggregate_money(sales.filter(payment_method=Sale.PaymentMethod.MOBILE_MONEY), "amount") + aggregate_money(product_sales.filter(payment_method="mobile_money"), "total_amount")
    total_expenses = aggregate_expenses(target_date, target_date)
    expenses = expense_queryset().filter(expense_date=target_date)

    day_items = apply_date_range(
        SaleItem.objects.filter(sale__status=Sale.Status.APPROVED).select_related("employee", "support_employee", "service"),
        target_date,
        target_date,
        field_prefix="sale__created_at",
    )
    employee_totals_map = {}
    for item in day_items:
        if item.employee_id:
            row = employee_totals_map.setdefault(item.employee_id, {
                "name": item.employee.name,
                "revenue": DECIMAL_ZERO,
                "main_commission": DECIMAL_ZERO,
                "support_commission": DECIMAL_ZERO,
                "commission": DECIMAL_ZERO,
            })
            row["revenue"] += item.price or DECIMAL_ZERO
            row["main_commission"] += item.commission_amount or DECIMAL_ZERO
            row["commission"] += item.commission_amount or DECIMAL_ZERO
        if item.support_employee_id and item.support_commission_amount:
            row = employee_totals_map.setdefault(item.support_employee_id, {
                "name": item.support_employee.name,
                "revenue": DECIMAL_ZERO,
                "main_commission": DECIMAL_ZERO,
                "support_commission": DECIMAL_ZERO,
                "commission": DECIMAL_ZERO,
            })
            row["support_commission"] += item.support_commission_amount or DECIMAL_ZERO
            row["commission"] += item.support_commission_amount or DECIMAL_ZERO
    employee_totals = sorted(employee_totals_map.values(), key=lambda r: (-r["commission"], -r["revenue"], r["name"].lower()))

    return {
        "target_date": target_date,
        "sales": sales,
        "product_sales": product_sales,
        "service_sales_total": service_sales_total,
        "product_sales_total": product_sales_total,
        "products_sold_count": sum((sale.quantity for sale in product_sales), 0),
        "total_sales": total_sales,
        "total_commission": total_commission,
        "total_support_commission": total_support_commission,
        "cash_total": cash_total,
        "mobile_money_total": mobile_money_total,
        "net_revenue": total_sales - total_commission,
        "total_expenses": total_expenses,
        "net_profit": total_sales - total_commission - total_expenses,
        "expenses": expenses,
        "expense_count": expenses.count(),
        "transaction_count": sales.count() + product_sales.count(),
        "service_transaction_count": sales.count(),
        "product_transaction_count": product_sales.count(),
        "employee_totals": employee_totals,
    }


def get_employee_report(start_date=None, end_date=None):
    items_qs = apply_date_range(
        SaleItem.objects.filter(
            sale__status=Sale.Status.APPROVED
        ).select_related("employee", "support_employee", "service", "sale"),
        start_date,
        end_date,
        field_prefix="sale__created_at",
    )

    employee_rows = {}

    def get_row(emp):
        return employee_rows.setdefault(
            emp.pk,
            {
                "employee_id": emp.pk,
                "employee_name": emp.name,
                "jobs_done": 0,
                "support_jobs_done": 0,
                "total_sales": DECIMAL_ZERO,
                "total_commission": DECIMAL_ZERO,
                "main_commission": DECIMAL_ZERO,
                "support_commission": DECIMAL_ZERO,
                "service_map": {},
            },
        )

    for item in items_qs:
        if item.employee_id:
            emp = item.employee
            row = get_row(emp)
            row["jobs_done"] += 1
            row["total_sales"] += item.price or DECIMAL_ZERO
            row["total_commission"] += item.commission_amount or DECIMAL_ZERO
            row["main_commission"] += item.commission_amount or DECIMAL_ZERO

            service_row = row["service_map"].setdefault(
                item.service_id,
                {
                    "service_name": item.service.name,
                    "jobs_done": 0,
                    "support_jobs_done": 0,
                    "total_revenue": DECIMAL_ZERO,
                    "total_commission": DECIMAL_ZERO,
                    "main_commission": DECIMAL_ZERO,
                    "support_commission": DECIMAL_ZERO,
                    "commission_rates": [],
                },
            )
            service_row["jobs_done"] += 1
            service_row["total_revenue"] += item.price or DECIMAL_ZERO
            service_row["total_commission"] += item.commission_amount or DECIMAL_ZERO
            service_row["main_commission"] += item.commission_amount or DECIMAL_ZERO
            if item.commission_rate is not None:
                service_row["commission_rates"].append(item.commission_rate)
            elif getattr(emp, "commission_type", None) == "percentage":
                service_row["commission_rates"].append(emp.commission_value)

        if item.support_employee_id and item.support_commission_amount:
            emp = item.support_employee
            row = get_row(emp)
            row["support_jobs_done"] += 1
            row["total_commission"] += item.support_commission_amount or DECIMAL_ZERO
            row["support_commission"] += item.support_commission_amount or DECIMAL_ZERO

            service_row = row["service_map"].setdefault(
                item.service_id,
                {
                    "service_name": item.service.name,
                    "jobs_done": 0,
                    "support_jobs_done": 0,
                    "total_revenue": DECIMAL_ZERO,
                    "total_commission": DECIMAL_ZERO,
                    "main_commission": DECIMAL_ZERO,
                    "support_commission": DECIMAL_ZERO,
                    "commission_rates": [],
                },
            )
            service_row["support_jobs_done"] += 1
            service_row["total_commission"] += item.support_commission_amount or DECIMAL_ZERO
            service_row["support_commission"] += item.support_commission_amount or DECIMAL_ZERO

    rows = []

    for row in employee_rows.values():
        row["net_revenue"] = row["total_sales"] - row["total_commission"]
        row["total_jobs"] = row["jobs_done"] + row["support_jobs_done"]

        breakdown = []
        for srow in row.pop("service_map").values():
            rates = srow.pop("commission_rates", [])
            if rates:
                avg = sum(rates) / len(rates)
                srow["commission_rate_display"] = avg.quantize(Decimal("0.01"))
            else:
                srow["commission_rate_display"] = None
            srow["total_jobs"] = srow["jobs_done"] + srow["support_jobs_done"]
            breakdown.append(srow)

        row["service_breakdown"] = sorted(
            breakdown,
            key=lambda e: (
                -e["total_commission"],
                -e["total_revenue"],
                e["service_name"].lower(),
            ),
        )
        row["service_count"] = len(row["service_breakdown"])
        rows.append(row)

    rows.sort(
        key=lambda e: (
            -e["total_commission"],
            -e["total_sales"],
            e["employee_name"].lower(),
        )
    )

    return rows

def get_service_report(start_date=None, end_date=None):
    sale_items = apply_date_range(
        SaleItem.objects.filter(sale__status=Sale.Status.APPROVED),
        start_date,
        end_date,
        field_prefix="sale__created_at",
    )

    return (
        sale_items.values("service__id", "service__name")
        .annotate(
            jobs_done=Count("id"),
            total_revenue=Coalesce(Sum("price"), ZERO),
        )
        .order_by("-jobs_done", "-total_revenue", "service__name")
    )