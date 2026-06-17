from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from apps.core.models import ActivityAlert, AuditLog
from apps.employees.models import Employee
from apps.inventory.models import Product, ServiceStockUsage, StockEntry
from apps.inventory.services import apply_service_stock_usage
from apps.sales.models import Sale, SaleItem
from apps.services.models import Service


class ServiceStockUsageTests(TestCase):
    def setUp(self):
        self.employee = Employee.objects.create(
            name="Martha",
            national_id="CM1234567890AD",
            commission_type=Employee.CommissionType.PERCENTAGE,
            commission_value=Decimal("50.00"),
        )
        self.service = Service.objects.create(name="Hair Dye", price=Decimal("50000"))
        self.product = Product.objects.create(
            name="Dye Pack",
            product_type=Product.ProductType.CONSUMABLE,
            unit="pack",
            buying_price=Decimal("8000"),
            low_stock_threshold=3,
        )
        StockEntry.objects.create(
            product=self.product,
            entry_type=StockEntry.EntryType.RESTOCK,
            quantity=5,
            date=timezone.localdate(),
        )
        ServiceStockUsage.objects.create(service=self.service, product=self.product, quantity=Decimal("2.00"))

    def test_approved_service_auto_deducts_configured_stock_once(self):
        sale = Sale.objects.create(
            employee=self.employee,
            service=self.service,
            amount=Decimal("50000"),
            status=Sale.Status.APPROVED,
            created_at=timezone.now(),
        )
        SaleItem.objects.create(sale=sale, service=self.service, employee=self.employee, price=Decimal("50000"))

        first_entries = apply_service_stock_usage(sale)
        second_entries = apply_service_stock_usage(sale)

        self.product.refresh_from_db()
        self.assertEqual(len(first_entries), 1)
        self.assertEqual(second_entries, [])
        self.assertEqual(self.product.current_stock, 3)
        self.assertTrue(AuditLog.objects.filter(action=AuditLog.Action.STOCK_USED, object_id=sale.pk).exists())
        self.assertTrue(ActivityAlert.objects.filter(dedupe_key=f"product:{self.product.pk}:low-stock").exists())
