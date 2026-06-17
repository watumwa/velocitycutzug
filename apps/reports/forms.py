from django import forms

from .models import DailyCloseout


class DailyCloseoutForm(forms.ModelForm):
    class Meta:
        model = DailyCloseout
        fields = [
            "counted_cash",
            "mobile_money_confirmed",
            "mobile_money_reference",
            "pending_approvals_confirmed",
            "expenses_confirmed",
            "commissions_confirmed",
            "notes",
        ]
        widgets = {
            "counted_cash": forms.NumberInput(attrs={"min": "0", "step": "1", "placeholder": "Cash counted in drawer"}),
            "mobile_money_reference": forms.TextInput(attrs={"placeholder": "Till statement, batch ID, or confirmation note"}),
            "notes": forms.Textarea(attrs={"rows": 4, "placeholder": "Shortage reason, handover notes, or owner comments"}),
        }
        labels = {
            "counted_cash": "Actual cash counted",
            "mobile_money_confirmed": "Mobile money statement matches the system",
            "pending_approvals_confirmed": "Pending approvals have been cleared",
            "expenses_confirmed": "Expenses paid today have been recorded",
            "commissions_confirmed": "Employee commissions have been checked",
        }

    def clean_counted_cash(self):
        counted_cash = self.cleaned_data.get("counted_cash")
        if counted_cash is not None and counted_cash < 0:
            raise forms.ValidationError("Counted cash cannot be negative.")
        return counted_cash

    def clean(self):
        cleaned = super().clean()
        required_checks = [
            "mobile_money_confirmed",
            "pending_approvals_confirmed",
            "expenses_confirmed",
            "commissions_confirmed",
        ]
        for field in required_checks:
            if not cleaned.get(field):
                self.add_error(field, "Confirm this before closing the day.")
        return cleaned
