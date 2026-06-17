from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from apps.customers.models import Customer
from apps.employees.models import Employee
from apps.sales.forms import SaleForm
from apps.sales.models import Sale, SaleItem
from apps.services.models import Service


class SaleModelTests(TestCase):
    def setUp(self):
        self.employee = Employee.objects.create(
            name="Sarah",
            national_id="CM1234567890AB",
            commission_type=Employee.CommissionType.PERCENTAGE,
            commission_value=Decimal("40.00"),
        )
        self.service = Service.objects.create(name="Haircut", price=Decimal("10000"))
        self.extra_service = Service.objects.create(name="Wash", price=Decimal("15000"))
        self.customer = Customer.objects.create(name="Jane")

    def _make_sale(self, amount, service=None, employee=None):
        service = service or self.service
        employee = employee or self.employee
        sale = Sale.objects.create(
            customer=self.customer,
            employee=employee,
            service=service,
            amount=amount,
            created_at=timezone.now(),
        )
        item = SaleItem.objects.create(sale=sale, service=service, employee=employee, price=amount)
        sale.recalculate_commission()
        return sale

    def test_sale_uses_service_price_and_calculates_commission(self):
        sale = self._make_sale(self.service.price)
        self.assertEqual(sale.amount, Decimal("10000"))
        self.assertEqual(sale.commission_amount, Decimal("4000"))

    def test_fixed_commission_employee_uses_fixed_value(self):
        employee = Employee.objects.create(
            name="Paul",
            national_id="CA1234567890BC",
            commission_type=Employee.CommissionType.FIXED,
            commission_value=Decimal("5000.00"),
        )
        sale = self._make_sale(Decimal("18000"), employee=employee)
        self.assertEqual(sale.commission_amount, Decimal("5000"))

    def test_sale_form_creates_multiple_service_items(self):
        form = SaleForm(data={
            "customer": self.customer.pk,
            f"employee_for_{self.service.pk}": self.employee.pk,
            f"employee_for_{self.extra_service.pk}": self.employee.pk,
            "services": [self.service.pk, self.extra_service.pk],
            "created_at": timezone.localtime().strftime("%Y-%m-%dT%H:%M"),
            "notes": "Bundle sale",
        })
        self.assertTrue(form.is_valid(), form.errors)
        sale = form.save()

        self.assertEqual(sale.amount, Decimal("25000"))
        self.assertEqual(sale.commission_amount, Decimal("10000"))
        self.assertEqual(sale.item_count, 2)
        self.assertEqual(sale.service_summary, "Haircut, Wash")
        self.assertEqual(sale.items.count(), 2)

    def test_manual_bundle_amount_is_distributed_across_sale_items(self):
        form = SaleForm(data={
            f"employee_for_{self.service.pk}": self.employee.pk,
            f"employee_for_{self.extra_service.pk}": self.employee.pk,
            "services": [self.service.pk, self.extra_service.pk],
            "amount": "20000",
            "created_at": timezone.localtime().strftime("%Y-%m-%dT%H:%M"),
        })
        self.assertTrue(form.is_valid(), form.errors)
        sale = form.save()

        self.assertEqual(sale.amount, Decimal("20000"))
        self.assertEqual(sum((item.price for item in sale.items.all()), Decimal("0")), Decimal("20000"))
