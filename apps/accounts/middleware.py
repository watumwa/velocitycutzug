from django.conf import settings
from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse


class PasswordChangeRequiredMiddleware:
    """Force employee accounts using the default password to change it immediately."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            employee = getattr(request.user, "employee_profile", None)
            if employee and employee.must_change_password and not request.user.is_superuser:
                allowed_paths = {reverse("accounts:password_change"), reverse("accounts:logout")}
                path = request.path
                static_url = getattr(settings, "STATIC_URL", "/static/")
                media_url = getattr(settings, "MEDIA_URL", "/media/")
                if (
                    path not in allowed_paths
                    and not path.startswith(static_url)
                    and not path.startswith(media_url)
                    and not path.startswith("/admin/")
                ):
                    messages.info(request, "Please change your default password before continuing.")
                    return redirect("accounts:password_change")
        return self.get_response(request)
