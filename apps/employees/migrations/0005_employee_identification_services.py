from django.db import migrations, models
from django.db.models import Q


def copy_existing_identification_and_services(apps, schema_editor):
    Employee = apps.get_model("employees", "Employee")
    for employee in Employee.objects.all():
        update_fields = []
        if getattr(employee, "national_id", None) and not getattr(employee, "id_number", None):
            employee.id_type = "national_id"
            employee.id_number = employee.national_id
            update_fields.extend(["id_type", "id_number"])
        if update_fields:
            employee.save(update_fields=update_fields)
        if getattr(employee, "service_id", None):
            employee.services.add(employee.service_id)


class Migration(migrations.Migration):

    dependencies = [
        ("employees", "0004_roles_departments_accounts"),
        ("services", "0003_service_photo"),
    ]

    operations = [
        migrations.AddField(
            model_name="employee",
            name="id_type",
            field=models.CharField(
                choices=[
                    ("national_id", "National ID"),
                    ("driving_license", "Driving Licence"),
                    ("refugee_id", "Refugee ID"),
                    ("passport", "Passport"),
                    ("other", "Other"),
                ],
                default="national_id",
                max_length=30,
                verbose_name="ID type",
            ),
        ),
        migrations.AddField(
            model_name="employee",
            name="id_number",
            field=models.CharField(
                blank=True,
                help_text="Enter National ID, Driving Licence, Refugee ID, Passport, or other ID number.",
                max_length=50,
                verbose_name="ID number",
            ),
        ),
        migrations.AddField(
            model_name="employee",
            name="services",
            field=models.ManyToManyField(
                blank=True,
                help_text="Services this employee is allowed to submit/work on.",
                related_name="employees",
                to="services.service",
            ),
        ),
        migrations.RunPython(copy_existing_identification_and_services, migrations.RunPython.noop),
        migrations.AddConstraint(
            model_name="employee",
            constraint=models.UniqueConstraint(
                fields=("id_type", "id_number"),
                condition=~Q(id_number=""),
                name="unique_employee_id_type_number",
            ),
        ),
    ]
