from apps.accounts.permissions import is_admin_user

from .models import ActivityAlert


def owner_activity_alerts(request):
    if not getattr(request, "user", None) or not request.user.is_authenticated or not is_admin_user(request.user):
        return {
            "open_activity_alert_count": 0,
            "recent_activity_alerts": [],
        }
    qs = ActivityAlert.objects.filter(resolved=False)
    return {
        "open_activity_alert_count": qs.count(),
        "recent_activity_alerts": qs[:5],
    }
