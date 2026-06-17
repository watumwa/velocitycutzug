from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def mark_existing_sales_approved(apps, schema_editor):
    Sale = apps.get_model("sales", "Sale")
    for sale in Sale.objects.all():
        sale.status = "approved"
        sale.approved_at = sale.created_at
        sale.save(update_fields=["status", "approved_at"])


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("sales", "0004_saleitem_commission_rate_override"),
    ]

    operations = [
        migrations.AddField(
            model_name="sale",
            name="status",
            field=models.CharField(
                choices=[
                    ("pending", "Pending Approval"),
                    ("approved", "Approved"),
                    ("rejected", "Rejected"),
                    ("cancelled", "Cancelled"),
                ],
                db_index=True,
                default="approved",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="sale",
            name="submitted_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="submitted_sales",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name="sale",
            name="approved_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="approved_sales",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name="sale",
            name="approved_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.RunPython(mark_existing_sales_approved, migrations.RunPython.noop),
    ]
