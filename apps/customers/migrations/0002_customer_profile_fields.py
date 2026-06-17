# Generated for UX/customer-profile improvements.
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("customers", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="customer",
            name="birthday",
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="customer",
            name="notes",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="customer",
            name="preferences",
            field=models.CharField(blank=True, help_text="Haircut style, barber preference, allergies, or service notes.", max_length=255),
        ),
        migrations.AddIndex(
            model_name="customer",
            index=models.Index(fields=["phone"], name="customers_c_phone_d9a31a_idx"),
        ),
        migrations.AddIndex(
            model_name="customer",
            index=models.Index(fields=["name"], name="customers_c_name_f3379c_idx"),
        ),
    ]
