from functools import wraps

from django.contrib import messages
from django.shortcuts import redirect

ADMIN = "admin"
CASHIER = "cashier"
EMPLOYEE = "employee"


def employee_profile(user):
    if not getattr(user, "is_authenticated", False):
        return None
    return getattr(user, "employee_profile", None)


def role_code(user):
    profile = employee_profile(user)
    return getattr(getattr(profile, "role", None), "code", None)


def is_admin_user(user):
    return bool(getattr(user, "is_superuser", False) or role_code(user) == ADMIN)


def is_cashier_user(user):
    return role_code(user) == CASHIER


def is_employee_user(user):
    return role_code(user) == EMPLOYEE


def has_any_role(user, *codes):
    return is_admin_user(user) or role_code(user) in codes


def role_required(*codes):
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if has_any_role(request.user, *codes):
                return view_func(request, *args, **kwargs)
            messages.error(request, "You do not have permission to open that page.")
            return redirect("home")
        return wrapper
    return decorator
