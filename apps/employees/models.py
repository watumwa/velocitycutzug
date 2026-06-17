import re
from decimal import Decimal
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator
from django.db import models
from django.db.models import Q
from django.utils.text import slugify

from apps.core.models import TimeStampedModel
from apps.core.utils import HUNDRED, quantize_ugx
from apps.services.models import Service

UGANDA_NATIONAL_ID_PATTERN = re.compile(r"^[CA][A-Z0-9]{13}$")
DEFAULT_EMPLOYEE_PASSWORD = "123"


class Role(TimeStampedModel):
    class Code(models.TextChoices):
        ADMIN = "admin", "Admin"
        CASHIER = "cashier", "Cashier"
        EMPLOYEE = "employee", "Employee"

    code = models.CharField(max_length=30, choices=Code.choices, unique=True)
    name = models.CharField(max_length=60, unique=True)
    description = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name

    @classmethod
    def default_employee_role(cls):
        role, _ = cls.objects.get_or_create(
            code=cls.Code.EMPLOYEE,
            defaults={"name": "Employee", "description": "General employee access"},
        )
        return role


class Department(TimeStampedModel):
    name = models.CharField(max_length=100, unique=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


def normalize_national_id(value: str) -> str:
    return re.sub(r"[\s-]+", "", (value or "").upper()).strip()


def validate_national_id(value: str) -> None:
    normalized = normalize_national_id(value)
    if not normalized:
        return
    if len(normalized) != 14:
        raise ValidationError("National ID must be exactly 14 characters.")
    if not UGANDA_NATIONAL_ID_PATTERN.match(normalized):
        raise ValidationError(
            "National ID must start with C or A and contain only letters and numbers."
        )


def unique_employee_username(employee, user_model):
    digits = re.sub(r"\D+", "", employee.phone or "")
    if digits:
        base = f"emp{digits[-9:]}"
    else:
        base = slugify(employee.name or "employee").replace("-", ".") or "employee"

    candidate = base[:140]
    counter = 1
    qs = user_model.objects.all()
    if employee.user_id:
        qs = qs.exclude(pk=employee.user_id)
    while qs.filter(username=candidate).exists():
        counter += 1
        suffix = f".{counter}"
        candidate = f"{base[:150-len(suffix)]}{suffix}"
    return candidate


class Employee(TimeStampedModel):
    class CommissionType(models.TextChoices):
        PERCENTAGE = "percentage", "Percentage"
        FIXED = "fixed", "Fixed Amount"

    class IdentificationType(models.TextChoices):
        NATIONAL_ID = "national_id", "National ID"
        DRIVING_LICENSE = "driving_license", "Driving Licence"
        REFUGEE_ID = "refugee_id", "Refugee ID"
        PASSPORT = "passport", "Passport"
        OTHER = "other", "Other"

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="employee_profile",
        help_text="System login account for this employee.",
    )
    role = models.ForeignKey(
        Role,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="employees",
    )
    department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="employees",
    )
    name = models.CharField(max_length=100)
    phone = models.CharField(max_length=20, blank=True)
    # Kept for backwards compatibility with older records. New entries use id_type + id_number.
    national_id = models.CharField(max_length=14, unique=True, null=True, blank=True)
    id_type = models.CharField(
        max_length=30,
        choices=IdentificationType.choices,
        default=IdentificationType.NATIONAL_ID,
        verbose_name="ID type",
    )
    id_number = models.CharField(
        max_length=50,
        blank=True,
        verbose_name="ID number",
        help_text="Enter National ID, Driving Licence, Refugee ID, Passport, or other ID number.",
    )
    photo = models.FileField(
        upload_to="employees/photos/",
        blank=True,
        validators=[FileExtensionValidator(allowed_extensions=["jpg", "jpeg", "png", "webp","HEIF"])],
        help_text="Upload JPG, JPEG, PNG, or WEBP. /Live Photos on shared hosting.",
    )
    commission_type = models.CharField(
        max_length=20,
        choices=CommissionType.choices,
        default=CommissionType.PERCENTAGE,
    )
    commission_value = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    is_active = models.BooleanField(default=True)
    # Legacy single service. Use services for new setups where an employee can perform many services.
    service = models.ForeignKey(Service, on_delete=models.SET_NULL, null=True, blank=True)
    services = models.ManyToManyField(
        Service,
        blank=True,
        related_name="employees",
        help_text="Services this employee is allowed to submit/work on.",
    )
    must_change_password = models.BooleanField(
        default=True,
        help_text="Employees created with the default password must change it after first login.",
    )

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["id_type", "id_number"],
                condition=~Q(id_number=""),
                name="unique_employee_id_type_number",
            )
        ]

    def __str__(self) -> str:
        return self.name

    @property
    def role_code(self) -> str:
        return self.role.code if self.role_id else Role.Code.EMPLOYEE

    @property
    def is_admin_role(self) -> bool:
        return self.role_code == Role.Code.ADMIN

    @property
    def is_cashier_role(self) -> bool:
        return self.role_code == Role.Code.CASHIER

    @property
    def is_employee_role(self) -> bool:
        return self.role_code == Role.Code.EMPLOYEE

    def clean(self) -> None:
        super().clean()
        self.id_number = (self.id_number or "").strip()
        if self.id_type == self.IdentificationType.NATIONAL_ID and self.id_number:
            self.id_number = normalize_national_id(self.id_number)
            validate_national_id(self.id_number)
            self.national_id = self.id_number
        elif self.id_type != self.IdentificationType.NATIONAL_ID:
            self.national_id = None

    @property
    def identification_display(self) -> str:
        if self.id_number:
            return f"{self.get_id_type_display()}: {self.id_number}"
        if self.national_id:
            return f"National ID: {self.national_id}"
        return "-"

    def allowed_services(self):
        services = self.services.filter(is_active=True)
        if services.exists():
            return services
        if self.service_id:
            return Service.objects.filter(pk=self.service_id, is_active=True)
        return Service.objects.none()

    def save(self, *args, **kwargs):
        self.id_number = (self.id_number or "").strip()
        if self.id_type == self.IdentificationType.NATIONAL_ID and self.id_number:
            self.id_number = normalize_national_id(self.id_number)
            self.national_id = self.id_number
        elif self.id_type != self.IdentificationType.NATIONAL_ID:
            self.national_id = None
        else:
            self.national_id = None
        self._resize_photo_safely()
        return super().save(*args, **kwargs)

    def _resize_photo_safely(self):
        """Leave uploaded employee photos untouched on shared hosting.

        Earlier versions tried to resize images with Pillow during every employee
        save. On some cPanel/Namecheap environments that can fail even when the
        uploaded file extension is correct, especially after the file has already
        been committed to storage. Django will now simply save the uploaded JPG,
        JPEG, PNG, or WEBP file after form validation.
        """
        return

    def calculate_commission(self, amount: Decimal) -> Decimal:
        amount = quantize_ugx(amount)
        if self.commission_type == self.CommissionType.PERCENTAGE:
            return quantize_ugx((amount * self.commission_value) / HUNDRED)
        return quantize_ugx(self.commission_value)

    def sync_user_account(self, reset_password: bool = False):
        """Create/update the linked login account. New staff use password 123."""
        User = get_user_model()
        if not self.role_id:
            self.role = Role.default_employee_role()
            Employee.objects.filter(pk=self.pk).update(role=self.role)

        if self.user_id:
            user = self.user
            created = False
        else:
            username = unique_employee_username(self, User)
            user = User(username=username)
            user.set_password(DEFAULT_EMPLOYEE_PASSWORD)
            created = True

        name_parts = (self.name or "").strip().split(maxsplit=1)
        user.first_name = name_parts[0] if name_parts else ""
        user.last_name = name_parts[1] if len(name_parts) > 1 else ""
        user.is_active = self.is_active
        user.is_staff = self.is_admin_role
        user.save()

        group, _ = Group.objects.get_or_create(name=self.role.name if self.role_id else "Employee")
        user.groups.set([group])

        if created:
            self.user = user
            self.must_change_password = True
            Employee.objects.filter(pk=self.pk).update(user=user, must_change_password=True)
        elif reset_password:
            user.set_password(DEFAULT_EMPLOYEE_PASSWORD)
            user.save(update_fields=["password"])
            self.must_change_password = True
            Employee.objects.filter(pk=self.pk).update(must_change_password=True)
        return user
