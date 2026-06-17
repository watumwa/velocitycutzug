from django.urls import path

from . import views

app_name = "customers"

urlpatterns = [
    path("", views.customer_list, name="list"),
    path("create/", views.customer_create, name="create"),
    path("<int:pk>/edit/", views.customer_update, name="edit"),
    path("<int:pk>/history/", views.customer_history, name="history"),
]
