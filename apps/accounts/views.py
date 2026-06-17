from django.contrib import messages
from django.contrib.auth import get_user_model, logout, update_session_auth_hash
from django.contrib.auth import views as auth_views
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponseRedirect
from django.urls import reverse_lazy
from django.views.decorators.http import require_POST

from .forms import SalonAuthenticationForm

User = get_user_model()


class SalonLoginView(auth_views.LoginView):
    template_name = "accounts/login.html"
    authentication_form = SalonAuthenticationForm
    redirect_authenticated_user = True

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["has_users"] = User.objects.exists()
        return context

    def form_valid(self, form):
        response = super().form_valid(form)
        if not form.cleaned_data.get("remember_me"):
            self.request.session.set_expiry(0)
        return response


class EmployeePasswordChangeView(LoginRequiredMixin, auth_views.PasswordChangeView):
    template_name = "accounts/password_change.html"
    success_url = reverse_lazy("home")

    def form_valid(self, form):
        response = super().form_valid(form)
        update_session_auth_hash(self.request, form.user)
        employee = getattr(self.request.user, "employee_profile", None)
        if employee:
            employee.must_change_password = False
            employee.save(update_fields=["must_change_password", "updated_at"])
        messages.success(self.request, "Password changed successfully.")
        return response


@require_POST
def logout_view(request):
    logout(request)
    return HttpResponseRedirect(reverse_lazy("accounts:login"))
