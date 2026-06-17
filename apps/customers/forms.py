from django import forms

from .models import Customer


class CustomerForm(forms.ModelForm):
    class Meta:
        model = Customer
        fields = ["name", "phone"]
        widgets = {
            "name": forms.TextInput(attrs={"placeholder": "Walk-in or customer name"}),
            "phone": forms.TextInput(attrs={"placeholder": "Optional phone number"}),
        }
