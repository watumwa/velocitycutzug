from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("inventory", "0003_rename_inventory_p_categor_1baf0a_idx_inventory_p_categor_062220_idx_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="productsale",
            name="payment_method",
            field=models.CharField(
                choices=[("cash", "Cash"), ("mobile_money", "Mobile Money")],
                db_index=True,
                default="cash",
                max_length=20,
            ),
        ),
    ]
