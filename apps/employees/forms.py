from django import forms

from .models import Department, Employee, Role, normalize_national_id, validate_national_id


class EmployeeForm(forms.ModelForm):
    class Meta:
        model = Employee
        fields = [
            "name", "phone", "id_type", "id_number", "role", "department", "services", "photo",
            "commission_type", "commission_value", "is_active",
        ]
        widgets = {
            "name": forms.TextInput(attrs={"placeholder": "Employee name"}),
            "phone": forms.TextInput(attrs={"placeholder": "2567..."}),
            "id_number": forms.TextInput(attrs={"placeholder": "Enter ID number"}),
            "services": forms.SelectMultiple(attrs={"size": "8"}),
            "photo": forms.ClearableFileInput(attrs={"accept": ".jpg,.jpeg,.png,.webp"}),
            "commission_value": forms.NumberInput(attrs={"min": "0", "step": "0.01"}),
        }
        help_texts = {
            "phone": "Used to help generate the login username when creating the employee account.",
            "id_type": "Choose the identification document the employee has.",
            "id_number": "National ID is optional. You can use Driving Licence, Refugee ID, Passport, or Other.",
            "services": "Select only the services this employee performs. Employee logins will only see these services.",
            "photo": "Optional employee picture in JPG, JPEG, PNG, or WEBP format. Avoid HEIF/Live Photos.",
            "commission_value": "Default commission. Haircut rules can still override this automatically at POS.",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["role"].queryset = Role.objects.all()
        self.fields["department"].queryset = Department.objects.filter(is_active=True)
        self.fields["role"].empty_label = "Select role"
        self.fields["department"].empty_label = "Select department"
        self.fields["role"].required = True
        self.fields["department"].required = True
        self.fields["id_number"].required = False
        self.fields["services"].required = False
        if not self.instance.pk:
            try:
                self.initial.setdefault("role", Role.default_employee_role())
            except Exception:
                pass
        elif self.instance.pk and self.instance.service_id and not self.instance.services.exists():
            self.initial.setdefault("services", [self.instance.service_id])


    def clean_photo(self):
        photo = self.cleaned_data.get("photo")
        if not photo:
            return photo

        # ClearableFileInput may return False when the user checks "clear".
        if photo is False:
            return photo

        name = getattr(photo, "name", "") or ""
        extension = name.rsplit(".", 1)[-1].lower() if "." in name else ""
        allowed = {"jpg", "jpeg", "png", "webp"}
        if extension not in allowed:
            raise forms.ValidationError("Upload only JPG, JPEG, PNG, or WEBP employee photos.")

        max_size = 5 * 1024 * 1024
        size = getattr(photo, "size", 0) or 0
        if size > max_size:
            raise forms.ValidationError("Employee photo is too large. Upload a photo below 5 MB.")

        return photo

    def clean_id_number(self):
        id_type = self.cleaned_data.get("id_type")
        id_number = (self.cleaned_data.get("id_number") or "").strip()

        if id_type == Employee.IdentificationType.NATIONAL_ID and id_number:
            id_number = normalize_national_id(id_number)
            validate_national_id(id_number)

        if id_number:
            duplicate = Employee.objects.filter(id_type=id_type, id_number=id_number)
            if self.instance.pk:
                duplicate = duplicate.exclude(pk=self.instance.pk)
            if duplicate.exists():
                raise forms.ValidationError("This ID number is already assigned to another employee.")
        return id_number

    def save(self, commit=True):
        employee = super().save(commit=False)
        if employee.id_type == Employee.IdentificationType.NATIONAL_ID and employee.id_number:
            employee.national_id = normalize_national_id(employee.id_number)
        else:
            employee.national_id = None
        if commit:
            employee.save()
            self.save_m2m()
            selected_services = self.cleaned_data.get("services")
            employee.service = selected_services.first() if selected_services else None
            employee.save(update_fields=["service", "national_id", "id_number", "id_type"])
            employee.sync_user_account()
        return employee
