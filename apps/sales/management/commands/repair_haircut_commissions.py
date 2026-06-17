from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.sales.models import Sale, SaleItem
from apps.sales.services import is_haircut_service
from apps.services.models import Service


class Command(BaseCommand):
    help = "Repair old UGX 15,000 haircut commissions and support commission setup."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show matching sale items without saving any changes.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        services = [
            service
            for service in Service.objects.filter(price=Decimal("15000")).order_by("id")
            if is_haircut_service(service)
        ]
        candidates = (
            SaleItem.objects.select_related("sale", "service", "employee")
            .filter(price=Decimal("15000"))
            .order_by("sale_id", "id")
        )

        items = [item for item in candidates if is_haircut_service(item.service)]
        sale_ids = sorted({item.sale_id for item in items})

        if not services and not items:
            self.stdout.write(self.style.SUCCESS("No UGX 15,000 haircut services or sale items found."))
            return

        for service in services:
            self.stdout.write(
                f"Service #{service.pk}: {service.name} - {service.price}, "
                f"support enabled {service.support_commission_enabled}, "
                f"support commission {service.support_commission_amount}"
            )

        for item in items:
            employee = item.employee.name if item.employee_id else "-"
            support_employee = item.support_employee.name if item.support_employee_id else "-"
            self.stdout.write(
                f"SaleItem #{item.pk}: sale #{item.sale_id}, {item.service.name}, "
                f"{employee}, support {support_employee}, old rate {item.commission_rate}, "
                f"old commission {item.commission_amount}, old support {item.support_commission_amount}"
            )

        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    f"Dry run only. {len(services)} service(s) would be set to support UGX 2,000. "
                    f"{len(items)} item(s) across {len(sale_ids)} sale(s) would be recalculated."
                )
            )
            return

        with transaction.atomic():
            service_ids = [service.pk for service in services]
            Service.objects.filter(pk__in=service_ids).update(
                support_commission_enabled=True,
                support_commission_amount=Decimal("2000"),
            )
            for sale in Sale.objects.filter(pk__in=sale_ids).prefetch_related("items"):
                sale.recalculate_commission()

        self.stdout.write(
            self.style.SUCCESS(
                f"Updated {len(services)} service(s) to support UGX 2,000 and recalculated "
                f"{len(items)} item(s) across {len(sale_ids)} sale(s). "
                "UGX 15,000 haircut commissions now pay UGX 4,000 main plus support where selected."
            )
        )
