from django.urls import path
from . import views

app_name = "inventory"

urlpatterns = [
    path("", views.product_list, name="list"),
    path("add/", views.product_create, name="create"),
    path("product-sales/", views.product_sale_list, name="product_sales"),
    path("product-sales/add/", views.product_sale_create, name="product_sale_create"),
    path("<int:pk>/sell/", views.product_sale_create, name="sell"),
    path("<int:pk>/edit/", views.product_edit, name="edit"),
    path("<int:pk>/stock/", views.stock_entry, name="stock"),
]
