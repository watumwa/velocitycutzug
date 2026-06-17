from django.urls import path

from .views import EmployeePasswordChangeView, SalonLoginView, logout_view

app_name = "accounts"

urlpatterns = [
    path("login/", SalonLoginView.as_view(), name="login"),
    path("password/change/", EmployeePasswordChangeView.as_view(), name="password_change"),
    path("logout/", logout_view, name="logout"),
]
