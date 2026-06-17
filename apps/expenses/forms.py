from django import forms

from .models import Expense


class ExpenseForm(forms.ModelForm):
    class Meta:
        model = Expense
        fields = [
            "title",
            "category",
            "amount",
            "expense_date",
            "vendor",
            "payment_method",
            "receipt_number",
            "notes",
        ]
        widgets = {
            "title": forms.TextInput(attrs={"placeholder": "e.g. Rent, shampoo supplies, electricity"}),
            "amount": forms.NumberInput(attrs={"min": "0", "step": "1", "placeholder": "Amount in UGX"}),
            "expense_date": forms.DateInput(attrs={"type": "date"}),
            "vendor": forms.TextInput(attrs={"placeholder": "Supplier / payee"}),
            "receipt_number": forms.TextInput(attrs={"placeholder": "Receipt or reference number"}),
            "notes": forms.Textarea(attrs={"rows": 4, "placeholder": "Optional notes"}),
        }

    def clean_amount(self):
        amount = self.cleaned_data.get("amount")
        if amount is not None and amount <= 0:
            raise forms.ValidationError("Expense amount must be greater than zero.")
        return amount
