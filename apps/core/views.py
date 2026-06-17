from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import redirect, render
from django.utils import timezone

from apps.accounts.permissions import role_required

from .models import ActivityAlert, AuditLog


@login_required
@role_required("admin")
def audit_log_list(request):
    action = request.GET.get("action", "")
    q = (request.GET.get("q") or "").strip()
    logs = AuditLog.objects.select_related("actor", "content_type")
    if action:
        logs = logs.filter(action=action)
    if q:
        logs = logs.filter(object_repr__icontains=q)
    page = Paginator(logs, 30).get_page(request.GET.get("page"))
    return render(
        request,
        "core/audit_log.html",
        {
            "logs": page,
            "page_obj": page,
            "action_choices": AuditLog.Action.choices,
            "filter_action": action,
            "filter_q": q,
        },
    )


@login_required
@role_required("admin")
def activity_alert_list(request):
    if request.method == "POST":
        alert_id = request.POST.get("alert_id")
        qs = ActivityAlert.objects.filter(resolved=False)
        if alert_id:
            qs = qs.filter(pk=alert_id)
        qs.update(resolved=True, resolved_at=timezone.now(), resolved_by=request.user)
        messages.success(request, "Alert marked as resolved.")
        return redirect("core:alerts")

    status = request.GET.get("status", "open")
    alerts = ActivityAlert.objects.all()
    if status == "resolved":
        alerts = alerts.filter(resolved=True)
    elif status != "all":
        alerts = alerts.filter(resolved=False)
    page = Paginator(alerts, 30).get_page(request.GET.get("page"))
    return render(
        request,
        "core/activity_alerts.html",
        {"alerts": page, "page_obj": page, "filter_status": status},
    )
