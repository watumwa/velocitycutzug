from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from django.utils import timezone

from .models import ActivityAlert, AuditLog


def log_action(actor, action, obj, details=None):
    content_type = None
    object_id = None
    if obj is not None:
        content_type = ContentType.objects.get_for_model(obj, for_concrete_model=False)
        object_id = obj.pk
    return AuditLog.objects.create(
        actor=actor if getattr(actor, "is_authenticated", False) else None,
        action=action,
        content_type=content_type,
        object_id=object_id,
        object_repr=str(obj)[:220] if obj is not None else "System",
        details=details or {},
    )


def create_alert(title, message, severity="warning", dedupe_key=None, target_url=""):
    dedupe_key = dedupe_key or f"{severity}:{title}:{message}"[:180]
    alert, _ = ActivityAlert.objects.get_or_create(
        dedupe_key=dedupe_key,
        defaults={
            "title": title,
            "message": message,
            "severity": severity,
            "target_url": target_url,
        },
    )
    return alert


def resolve_alerts(prefix, user=None):
    qs = ActivityAlert.objects.filter(dedupe_key__startswith=prefix, resolved=False)
    qs.update(resolved=True, resolved_at=timezone.now(), resolved_by=user if getattr(user, "is_authenticated", False) else None)


def alert_large_expense(expense, threshold):
    if expense.amount >= threshold:
        create_alert(
            "Large expense recorded",
            f"{expense.title} was recorded for UGX {expense.amount:,.0f}.",
            severity="warning",
            dedupe_key=f"expense:{expense.pk}:large",
            target_url=reverse("expenses:list"),
        )


def alert_sale_rejected(sale):
    create_alert(
        "Sale submission rejected",
        f"{sale.service_summary} worth UGX {sale.amount:,.0f} was rejected.",
        severity="warning",
        dedupe_key=f"sale:{sale.pk}:rejected",
        target_url=reverse("sales:pending"),
    )


def alert_cash_variance(closeout):
    variance = closeout.cash_variance
    if variance:
        label = "shortage" if variance < 0 else "surplus"
        create_alert(
            f"Cash {label} on closeout",
            f"{closeout.business_date:%d %b %Y} closed with a UGX {abs(variance):,.0f} {label}.",
            severity="critical" if variance < 0 else "warning",
            dedupe_key=f"closeout:{closeout.pk}:variance",
            target_url=reverse("reports:closeout_history"),
        )


def alert_low_stock(product):
    if product.is_low_stock:
        create_alert(
            "Low stock",
            f"{product.name} is at {product.current_stock} {product.unit}; threshold is {product.low_stock_threshold}.",
            severity="critical" if product.is_out_of_stock else "warning",
            dedupe_key=f"product:{product.pk}:low-stock",
            target_url=reverse("inventory:list") + "?status=low",
        )
    else:
        resolve_alerts(f"product:{product.pk}:low-stock")
