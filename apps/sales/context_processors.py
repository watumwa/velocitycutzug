from decimal import Decimal

from django.db.models import Sum

from apps.accounts.permissions import CASHIER, has_any_role

from .models import Sale


def pending_sale_approvals(request):
    """Expose pending employee sale submissions to admin/cashier templates.

    Kept defensive so management commands such as migrate/collectstatic do not fail
    if the sales table has not been created yet.
    """
    defaults = {
        "pending_approval_count": 0,
        "pending_approval_total": Decimal("0"),
        "pending_approval_sales": [],
        "latest_pending_sale_id": "",
        "can_review_sale_approvals": False,
    }
    try:
        user = getattr(request, "user", None)
        if not getattr(user, "is_authenticated", False) or not has_any_role(user, CASHIER):
            return defaults

        defaults["can_review_sale_approvals"] = True
        qs = (
            Sale.objects.filter(status=Sale.Status.PENDING)
            .select_related("customer", "submitted_by")
            .prefetch_related("items__service", "items__employee")
            .order_by("-created_at", "-id")
        )
        latest = list(qs[:5])
        return {
            "pending_approval_count": qs.count(),
            "pending_approval_total": qs.aggregate(total=Sum("amount"))["total"] or Decimal("0"),
            "pending_approval_sales": latest,
            "latest_pending_sale_id": latest[0].pk if latest else "",
            "can_review_sale_approvals": True,
        }
    except Exception:
        return defaults
