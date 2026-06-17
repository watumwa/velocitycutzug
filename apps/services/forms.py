from django import forms

from .models import Service


class BaseServiceForm(forms.ModelForm):
    class Meta:
        model = Service
        fields = []
        widgets = {
            "name": forms.TextInput(attrs={"placeholder": "Signature blowout, premium braids, luxury manicure..."}),
            "price": forms.NumberInput(attrs={"min": "0", "step": "1", "placeholder": "25000"}),
            "support_commission_amount": forms.NumberInput(attrs={"min": "0", "step": "1", "placeholder": "0"}),
            "photo": forms.FileInput(attrs={"accept": ".jpg,.jpeg,.png,.webp"}),
        }


class ServiceForm(BaseServiceForm):
    class Meta(BaseServiceForm.Meta):
        fields = ["price", "support_commission_enabled", "support_commission_amount", "is_active", "photo"]


class CustomServiceForm(BaseServiceForm):
    class Meta(BaseServiceForm.Meta):
        fields = ["name", "price", "support_commission_enabled", "support_commission_amount", "is_active", "photo"]
