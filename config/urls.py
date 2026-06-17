from django.conf import settings
from django.contrib import admin
from django.urls import include, path, re_path
from django.views.static import serve

from apps.reports import views as report_views

urlpatterns = [
    # Force media serving on Namecheap production
    re_path(
        r"^media/(?P<path>.*)$",
        serve,
        {"document_root": settings.MEDIA_ROOT},
        name="media",
    ),

    path("admin/", admin.site.urls),
    path("auth/", include("apps.accounts.urls")),

    # Dashboard / home page
    path("", report_views.dashboard, name="home"),

    path("employees/", include("apps.employees.urls")),
    path("services/", include("apps.services.urls")),
    path("customers/", include("apps.customers.urls")),
    path("sales/", include("apps.sales.urls")),
    path("reports/", include("apps.reports.urls")),
    path("inventory/", include("apps.inventory.urls")),
    path("expenses/", include("apps.expenses.urls")),
]