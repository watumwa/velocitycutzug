from django.db import migrations


def seed_cashier_department(apps, schema_editor):
    Department = apps.get_model("employees", "Department")
    Department.objects.get_or_create(name="Cashier Department", defaults={"is_active": True})


class Migration(migrations.Migration):
    dependencies = [
        ("employees", "0007_alter_employee_photo"),
    ]

    operations = [
        migrations.RunPython(seed_cashier_department, migrations.RunPython.noop),
    ]
