from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("employees", "0007_alter_employee_photo"),
        ("sales", "0005_sale_approval_status"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.AddField(
                    model_name="sale",
                    name="payment_method",
                    field=models.CharField(
                        choices=[("cash", "Cash"), ("mobile_money", "Mobile Money")],
                        db_index=True,
                        default="cash",
                        max_length=20,
                    ),
                ),
            ],
        ),
        migrations.AddField(
            model_name="saleitem",
            name="support_employee",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="support_sale_items",
                to="employees.employee",
            ),
        ),
        migrations.AddField(
            model_name="saleitem",
            name="support_commission_amount",
            field=models.DecimalField(decimal_places=0, default=0, max_digits=12),
        ),
        migrations.AddIndex(
            model_name="sale",
            index=models.Index(
                fields=["status", "payment_method", "created_at"],
                name="sales_sale_status__3e0b1d_idx",
            ),
        ),
    ]