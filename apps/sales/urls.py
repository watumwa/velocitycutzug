from django.urls import path

from . import views

app_name = "sales"

urlpatterns = [
    path("", views.sale_list, name="list"),
    path("create/", views.create_sale, name="create"),
    path("pending-status/", views.pending_approvals_status, name="pending_status"),
    path("<int:pk>/edit/", views.edit_sale, name="edit"),
    path("<int:pk>/approve/", views.approve_sale, name="approve"),
    path("<int:pk>/reject/", views.reject_sale, name="reject"),
    path("<int:pk>/delete/", views.delete_sale, name="delete"),
]
