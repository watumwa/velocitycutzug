from datetime import timedelta
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from apps.employees.models import Employee
from apps.reports.services import (
    get_daily_report,
    get_dashboard_metrics,
    get_employee_report,
    get_service_report,
)
from apps.sales.models import Sale, SaleItem
from apps.services.models import Service


class ReportServiceTests(TestCase):
    def setUp(self):
        self.employee = Employee.objects.create(
            name="Martha",
            national_id="CM1234567890AB",
            commission_type=Employee.CommissionType.PERCENTAGE,
            commission_value=Decimal("50.00"),
        )
        self.service = Service.objects.create(name="Braiding", price=Decimal("30000"))
        today = timezone.now()
        yesterday = today - timedelta(days=1)

        today_sale = Sale.objects.create(
            employee=self.employee,
            service=self.service,
            amount=Decimal("30000"),
            created_at=today,
        )
        SaleItem.objects.create(
            sale=today_sale, service=self.service,
            employee=self.employee, price=Decimal("30000"),
        )
        today_sale.recalculate_commission()

        yesterday_sale = Sale.objects.create(
            employee=self.employee,
            service=self.service,
            amount=Decimal("15000"),
            created_at=yesterday,
        )
        SaleItem.objects.create(
            sale=yesterday_sale, service=self.service,
            employee=self.employee, price=Decimal("15000"),
        )
        yesterday_sale.recalculate_commission()

    def test_daily_report_sums_only_target_date(self):
        target_date = timezone.localdate()
        report = get_daily_report(target_date)

        self.assertEqual(report["total_sales"], Decimal("30000"))
        self.assertEqual(report["total_commission"], Decimal("15000"))
        self.assertEqual(report["net_revenue"], Decimal("15000"))
        self.assertEqual(report["transaction_count"], 1)

    def test_dashboard_metrics_include_net_revenue(self):
        metrics = get_dashboard_metrics()

        self.assertEqual(metrics["today_revenue"], Decimal("30000"))
        self.assertEqual(metrics["today_commission"], Decimal("15000"))
        self.assertEqual(metrics["today_net_revenue"], Decimal("15000"))
        self.assertEqual(metrics["week_revenue"], Decimal("45000"))
        self.assertEqual(metrics["week_net_revenue"], Decimal("22500"))
        self.assertEqual(metrics["month_revenue"], Decimal("45000"))
        self.assertEqual(metrics["month_net_revenue"], Decimal("22500"))

    def test_employee_report_aggregates_sales(self):
        rows = list(get_employee_report())
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["jobs_done"], 2)
        self.assertEqual(rows[0]["total_sales"], Decimal("45000"))

    def test_employee_report_includes_service_commission_breakdown(self):
        second_service = Service.objects.create(name="Wash", price=Decimal("10000"))
        mixed_sale = Sale.objects.create(
            employee=self.employee,
            service=self.service,
            amount=Decimal("40000"),
            created_at=timezone.now(),
        )
        SaleItem.objects.create(
            sale=mixed_sale, service=self.service,
            employee=self.employee, price=Decimal("30000"),
        )
        SaleItem.objects.create(
            sale=mixed_sale, service=second_service,
            employee=self.employee, price=Decimal("10000"),
        )
        mixed_sale.recalculate_commission()

        row = get_employee_report()[0]
        breakdown = {entry["service_name"]: entry for entry in row["service_breakdown"]}

        self.assertEqual(row["jobs_done"], 4)  # 2 from setUp + 2 items in mixed_sale
        self.assertEqual(row["total_sales"], Decimal("85000"))
        self.assertEqual(row["total_commission"], Decimal("42500"))
        self.assertEqual(row["net_revenue"], Decimal("42500"))
        self.assertEqual(breakdown["Braiding"]["jobs_done"], 3)
        self.assertEqual(breakdown["Braiding"]["total_revenue"], Decimal("75000"))
        self.assertEqual(breakdown["Braiding"]["total_commission"], Decimal("37500"))
        self.assertEqual(breakdown["Wash"]["jobs_done"], 1)
        self.assertEqual(breakdown["Wash"]["total_revenue"], Decimal("10000"))
        self.assertEqual(breakdown["Wash"]["total_commission"], Decimal("5000"))

    def test_service_report_aggregates_revenue(self):
        rows = list(get_service_report())
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["jobs_done"], 2)
        self.assertEqual(rows[0]["total_revenue"], Decimal("45000"))
