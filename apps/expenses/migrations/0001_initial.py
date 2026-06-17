# Generated manually for the expenses module.

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Expense",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=140)),
                ("category", models.CharField(choices=[("rent", "Rent"), ("utilities", "Utilities"), ("salaries", "Salaries"), ("inventory", "Inventory / Supplies"), ("cleaning", "Cleaning"), ("transport", "Transport"), ("marketing", "Marketing"), ("repairs", "Repairs & Maintenance"), ("taxes", "Taxes / Licences"), ("other", "Other")], db_index=True, default="other", max_length=30)),
                ("amount", models.DecimalField(decimal_places=0, max_digits=12)),
                ("expense_date", models.DateField(db_index=True, default=django.utils.timezone.localdate)),
                ("vendor", models.CharField(blank=True, help_text="Supplier, landlord, staff member, or payee.", max_length=120)),
                ("payment_method", models.CharField(choices=[("cash", "Cash"), ("mobile_money", "Mobile Money"), ("bank", "Bank Transfer"), ("card", "Card"), ("other", "Other")], default="cash", max_length=30)),
                ("receipt_number", models.CharField(blank=True, max_length=80)),
                ("notes", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("recorded_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="recorded_expenses", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "ordering": ["-expense_date", "-created_at", "-id"],
            },
        ),
        migrations.AddIndex(
            model_name="expense",
            index=models.Index(fields=["expense_date", "category"], name="expenses_ex_expense_9770d5_idx"),
        ),
    ]
