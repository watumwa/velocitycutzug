from decimal import Decimal, ROUND_HALF_UP

from django.db import transaction

from apps.core.audit import alert_low_stock, log_action
from apps.core.models import AuditLog

from .models import ServiceStockUsage, StockEntry


def _stock_quantity(value):
    return int(Decimal(value).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


@transaction.atomic
def apply_service_stock_usage(sale, actor=None):
    if not sale.is_approved:
        return []

    created_entries = []
    items = sale.items.select_related("service").prefetch_related("service__stock_usages__product")
    for item in items:
        usages = ServiceStockUsage.objects.filter(service=item.service, is_active=True).select_related("product")
        for usage in usages:
            if StockEntry.objects.filter(related_sale_item=item, product=usage.product, entry_type=StockEntry.EntryType.SERVICE_USAGE).exists():
                continue
            quantity = _stock_quantity(usage.quantity)
            if quantity <= 0:
                continue
            entry = StockEntry.objects.create(
                product=usage.product,
                entry_type=StockEntry.EntryType.SERVICE_USAGE,
                quantity=-abs(quantity),
                unit_cost=usage.product.buying_price,
                date=sale.created_at.date(),
                related_sale_item=item,
                note=f"Auto-used for sale #{sale.pk}: {item.service.name}",
            )
            created_entries.append(entry)
            alert_low_stock(usage.product)

    if created_entries:
        log_action(
            actor,
            AuditLog.Action.STOCK_USED,
            sale,
            {"entries": [{"product": e.product.name, "quantity": e.quantity} for e in created_entries]},
        )
    return created_entries
