from django.urls import path

from . import views

app_name = "reports"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("daily/", views.daily_summary, name="daily"),
    path("employees/", views.employee_report, name="employees"),
    path("my-commissions/", views.my_commissions, name="my_commissions"),
    path("services/", views.service_report, name="services"),
]
