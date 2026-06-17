from decimal import Decimal

from django import forms
from django.db import transaction
from django.utils import timezone

from apps.accounts.permissions import is_employee_user
from apps.customers.models import Customer
from apps.employees.models import Employee
from apps.services.models import Service

from .models import Sale, SaleItem
from .services import calculate_commission, commission_from_rate, haircut_commission_rate_for_price


class SaleForm(forms.ModelForm):
    services = forms.ModelMultipleChoiceField(
        queryset=Service.objects.none(),
        required=True,
        help_text="Choose one or more services.",
    )
    created_at = forms.DateTimeField(
        required=False,
        widget=forms.DateTimeInput(attrs={"type": "datetime-local"}),
    )

    class Meta:
        model = Sale
        fields = ["customer", "amount", "payment_method", "created_at", "notes"]
        widgets = {
            "customer": forms.Select(),
            "amount": forms.NumberInput(attrs={"min": "0", "step": "1"}),
            "payment_method": forms.Select(),
            "notes": forms.TextInput(attrs={"placeholder": "Optional note"}),
        }

    def __init__(self, *args, **kwargs):
        self.current_user = kwargs.pop("current_user", None)
        self.employee_profile = getattr(self.current_user, "employee_profile", None) if self.current_user else None
        self.is_employee_submission = bool(
            self.current_user
            and self.current_user.is_authenticated
            and is_employee_user(self.current_user)
            and not self.current_user.is_superuser
        )
        super().__init__(*args, **kwargs)
        self.fields["customer"].queryset = Customer.objects.all()
        self.fields["customer"].required = False
        self.fields["customer"].empty_label = "Walk-in / No customer"

        if self.is_employee_submission and self.employee_profile:
            self.fields["services"].queryset = self.employee_profile.allowed_services()
            self.fields["services"].help_text = "Only services assigned to your employee profile are shown here."
            self.fields["amount"].widget.attrs["readonly"] = "readonly"
            self.fields["amount"].help_text = "Auto-filled from selected service prices. Admin/cashier confirms payment method and support employee on approval."
            self.fields.pop("payment_method", None)
        else:
            self.fields["services"].queryset = Service.objects.filter(is_active=True)
            self.fields["amount"].help_text = "Auto-filled from service prices. You can override the total."
            self.fields["payment_method"].help_text = "For employee-submitted services, cashier/admin confirms this during approval."

        self.fields["amount"].required = False

        if self.instance.pk and self.instance.created_at:
            self.initial["created_at"] = self.instance.created_at.strftime("%Y-%m-%dT%H:%M")
            self.initial["services"] = self.instance.items.values_list("service_id", flat=True)
        elif not self.is_bound:
            self.initial["created_at"] = timezone.localtime().strftime("%Y-%m-%dT%H:%M")

    def clean_services(self):
        services = self.cleaned_data.get("services")
        if not services:
            raise forms.ValidationError("Select at least one service.")
        if self.is_employee_submission and self.employee_profile:
            allowed_ids = set(self.employee_profile.allowed_services().values_list("pk", flat=True))
            submitted_ids = set(services.values_list("pk", flat=True))
            if not submitted_ids.issubset(allowed_ids):
                raise forms.ValidationError("You can only submit services assigned to your profile.")
        return services

    def clean(self):
        cleaned_data = super().clean()
        services = cleaned_data.get("services")
        amount = cleaned_data.get("amount")
        if amount is None and services:
            cleaned_data["amount"] = sum((s.price for s in services), Decimal("0"))
        if cleaned_data.get("created_at") is None:
            cleaned_data["created_at"] = timezone.now()
        return cleaned_data

    def _get_employee_for_service(self, service):
        """Extract per-service main employee from POST data: employee_for_<service_pk>."""
        if self.is_employee_submission:
            return self.employee_profile
        key = f"employee_for_{service.pk}"
        emp_id = self.data.get(key)
        if emp_id:
            try:
                return Employee.objects.get(pk=emp_id, is_active=True)
            except Employee.DoesNotExist:
                pass
        return None

    def _get_support_employee_for_service(self, service, main_employee=None):
        """Extract optional support employee from POST data: support_employee_for_<service_pk>."""
        if self.is_employee_submission or not getattr(service, "support_commission_enabled", False):
            return None
        key = f"support_employee_for_{service.pk}"
        emp_id = self.data.get(key)
        if not emp_id:
            return None
        try:
            support_employee = Employee.objects.get(pk=emp_id, is_active=True)
        except Employee.DoesNotExist:
            return None
        if main_employee and support_employee.pk == main_employee.pk:
            return None
        return support_employee

    def _get_rate_for_service(self, service):
        """Extract optional commission rate override: commission_rate_for_<service_pk>."""
        if self.is_employee_submission:
            return None
        key = f"commission_rate_for_{service.pk}"
        val = self.data.get(key, "").strip()
        if val:
            try:
                rate = Decimal(val)
                if Decimal("0") <= rate <= Decimal("100"):
                    return rate
            except Exception:
                pass
        return None

    def _allocate_prices(self, services, total_amount):
        """Distribute total_amount proportionally by service price."""
        service_list = list(services)
        if not service_list:
            return []
        base_total = sum((s.price for s in service_list), Decimal("0"))
        total_int = int(total_amount)
        if len(service_list) == 1:
            return [(service_list[0], total_amount)]
        allocations = []
        running = 0
        base_int = int(base_total)
        for s in service_list[:-1]:
            share = (total_int * int(s.price)) // base_int if base_int else total_int // len(service_list)
            allocations.append((s, Decimal(share)))
            running += share
        allocations.append((service_list[-1], Decimal(total_int - running)))
        return allocations

    @transaction.atomic
    def save(self, commit=True):
        services = list(self.cleaned_data["services"])
        sale = super().save(commit=False)
        sale.service = services[0]
        sale.employee = self._get_employee_for_service(services[0])
        sale.amount = self.cleaned_data["amount"]
        sale.created_at = self.cleaned_data["created_at"]
        sale.submitted_by = self.current_user if getattr(self.current_user, "is_authenticated", False) else None

        if not self.is_employee_submission:
            sale.payment_method = self.cleaned_data.get("payment_method") or Sale.PaymentMethod.CASH

        if self.is_employee_submission:
            sale.status = Sale.Status.PENDING
            sale.approved_by = None
            sale.approved_at = None
            sale.commission_amount = 0
        elif not sale.pk or sale.status == Sale.Status.PENDING:
            # Cashier/admin-created records are approved immediately unless editing an existing rejected/cancelled record.
            sale.status = Sale.Status.APPROVED
            sale.approved_by = self.current_user if getattr(self.current_user, "is_authenticated", False) else None
            sale.approved_at = timezone.now()

        if not commit:
            return sale

        sale.save()
        sale.items.all().delete()

        items = []
        total_commission = Decimal("0")
        for service, price in self._allocate_prices(services, sale.amount):
            employee = self._get_employee_for_service(service)
            support_employee = self._get_support_employee_for_service(service, employee)
            manual_rate = self._get_rate_for_service(service)
            auto_rate = haircut_commission_rate_for_price(service, price)
            rate = manual_rate if manual_rate is not None else auto_rate

            main_commission = Decimal("0")
            support_commission = Decimal("0")
            if sale.status == Sale.Status.APPROVED:
                if employee:
                    if rate is not None:
                        main_commission = commission_from_rate(price, rate)
                    else:
                        main_commission = calculate_commission(employee, price)
                if support_employee and getattr(service, "support_commission_enabled", False):
                    support_commission = Decimal(getattr(service, "support_commission_amount", 0) or 0)

            total_commission += main_commission + support_commission
            items.append(SaleItem(
                sale=sale,
                service=service,
                employee=employee,
                support_employee=support_employee,
                price=price,
                commission_rate=rate,
                commission_amount=main_commission,
                support_commission_amount=support_commission,
            ))

        SaleItem.objects.bulk_create(items)
        sale.commission_amount = total_commission if sale.status == Sale.Status.APPROVED else Decimal("0")
        Sale.objects.filter(pk=sale.pk).update(commission_amount=sale.commission_amount)
        return sale
