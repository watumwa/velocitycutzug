from django import forms
from django.contrib.auth.forms import AuthenticationForm


class SalonAuthenticationForm(AuthenticationForm):
    remember_me = forms.BooleanField(required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].widget.attrs.update(
            {
                "placeholder": "Email or username",
                "autocomplete": "username",
                "autofocus": True,
                "spellcheck": "false",
            }
        )
        self.fields["password"].widget.attrs.update(
            {
                "placeholder": "Password",
                "autocomplete": "current-password",
            }
        )
