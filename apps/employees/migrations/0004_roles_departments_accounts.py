import re

import django.db.models.deletion
from django.conf import settings
from django.contrib.auth.hashers import make_password
from django.db import migrations, models

ROLE_SEEDS = [
    ("admin", "Admin", "Can manage the system and view all reports."),
    ("cashier", "Cashier", "Can record sales and serve customers."),
    ("employee", "Employee", "Can view own commissions and employee dashboard."),
]

DEPARTMENT_SEEDS = [
    "Mens Department",
    "Womens Department",
    "Pedicure and Manicure Department",
    "Cleaning Department",
]


def _username_for(employee, User):
    digits = re.sub(r"\D+", "", employee.phone or "")
    if digits:
        base = f"emp{digits[-9:]}"
    else:
        base = re.sub(r"[^a-zA-Z0-9]+", ".", (employee.name or "employee").strip().lower()).strip(".") or "employee"
    candidate = base[:140]
    counter = 1
    while User.objects.filter(username=candidate).exists():
        counter += 1
        suffix = f".{counter}"
        candidate = f"{base[:150-len(suffix)]}{suffix}"
    return candidate


def seed_roles_departments_accounts(apps, schema_editor):
    Role = apps.get_model("employees", "Role")
    Department = apps.get_model("employees", "Department")
    Employee = apps.get_model("employees", "Employee")
    User = apps.get_model("auth", "User")
    Group = apps.get_model("auth", "Group")

    roles = {}
    for code, name, description in ROLE_SEEDS:
        role, _ = Role.objects.get_or_create(code=code, defaults={"name": name, "description": description})
        roles[code] = role
        Group.objects.get_or_create(name=name)

    departments = []
    for name in DEPARTMENT_SEEDS:
        dept, _ = Department.objects.get_or_create(name=name, defaults={"is_active": True})
        departments.append(dept)

    default_role = roles["employee"]
    default_department = departments[0] if departments else None
    employee_group = Group.objects.get(name="Employee")

    for employee in Employee.objects.all():
        changed = []
        if not employee.role_id:
            employee.role = default_role
            changed.append("role")
        if not employee.department_id and default_department:
            employee.department = default_department
            changed.append("department")
        if not employee.user_id:
            name_parts = (employee.name or "").strip().split(maxsplit=1)
            user = User.objects.create(
                username=_username_for(employee, User),
                first_name=name_parts[0] if name_parts else "",
                last_name=name_parts[1] if len(name_parts) > 1 else "",
                password=make_password("123"),
                is_active=employee.is_active,
                is_staff=False,
            )
            user.groups.add(employee_group)
            employee.user = user
            employee.must_change_password = True
            changed.extend(["user", "must_change_password"])
        if changed:
            employee.save(update_fields=list(set(changed)))


class Migration(migrations.Migration):

    dependencies = [
        ("auth", "0012_alter_user_first_name_max_length"),
        ("employees", "0003_employee_service_alter_employee_photo"),
    ]

    operations = [
        migrations.CreateModel(
            name="Department",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("name", models.CharField(max_length=100, unique=True)),
                ("is_active", models.BooleanField(default=True)),
            ],
            options={"ordering": ["name"]},
        ),
        migrations.CreateModel(
            name="Role",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("code", models.CharField(choices=[("admin", "Admin"), ("cashier", "Cashier"), ("employee", "Employee")], max_length=30, unique=True)),
                ("name", models.CharField(max_length=60, unique=True)),
                ("description", models.CharField(blank=True, max_length=255)),
            ],
            options={"ordering": ["name"]},
        ),
        migrations.AddField(
            model_name="employee",
            name="must_change_password",
            field=models.BooleanField(default=True, help_text="Employees created with the default password must change it after first login."),
        ),
        migrations.AddField(
            model_name="employee",
            name="department",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="employees", to="employees.department"),
        ),
        migrations.AddField(
            model_name="employee",
            name="role",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="employees", to="employees.role"),
        ),
        migrations.AddField(
            model_name="employee",
            name="user",
            field=models.OneToOneField(blank=True, help_text="System login account for this employee.", null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="employee_profile", to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name="employee",
            name="commission_type",
            field=models.CharField(choices=[("percentage", "Percentage"), ("fixed", "Fixed Amount")], default="percentage", max_length=20),
        ),
        migrations.AlterField(
            model_name="employee",
            name="commission_value",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10),
        ),
        migrations.RunPython(seed_roles_departments_accounts, migrations.RunPython.noop),
    ]
