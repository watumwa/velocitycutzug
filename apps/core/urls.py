from django.urls import path

from . import views

app_name = "core"

urlpatterns = [
    path("audit/", views.audit_log_list, name="audit_log"),
    path("alerts/", views.activity_alert_list, name="alerts"),
]
