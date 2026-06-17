from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("customers", "0001_initial"),
        ("expenses", "0002_expand_expense_categories"),
        ("inventory", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="product",
            name="buying_price",
            field=models.DecimalField(decimal_places=0, default=0, help_text="Cost price per unit in UGX.", max_digits=12),
        ),
        migrations.AddField(
            model_name="product",
            name="category",
            field=models.CharField(
                choices=[
                    ("hair_care", "Hair Care"),
                    ("beard_care", "Beard Care"),
                    ("nails", "Nails / Pedicure"),
                    ("cleaning", "Cleaning Supplies"),
                    ("tools", "Tools & Equipment"),
                    ("consumables", "Salon Consumables"),
                    ("cosmetics", "Cosmetics"),
                    ("other", "Other"),
                ],
                db_index=True,
                default="other",
                max_length=30,
            ),
        ),
        migrations.AddField(
            model_name="product",
            name="expiry_date",
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="product",
            name="product_type",
            field=models.CharField(
                choices=[("retail", "For Sale"), ("consumable", "Salon Use Only"), ("both", "Sale + Salon Use")],
                db_index=True,
                default="retail",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="product",
            name="selling_price",
            field=models.DecimalField(decimal_places=0, default=0, help_text="Retail selling price per unit in UGX.", max_digits=12),
        ),
        migrations.AddField(
            model_name="product",
            name="supplier",
            field=models.CharField(blank=True, max_length=150),
        ),
        migrations.AddField(
            model_name="stockentry",
            name="related_expense",
            field=models.ForeignKey(blank=True, help_text="Automatically created expense for stock purchases when applicable.", null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="stock_entries", to="expenses.expense"),
        ),
        migrations.AddField(
            model_name="stockentry",
            name="supplier",
            field=models.CharField(blank=True, max_length=150),
        ),
        migrations.AddField(
            model_name="stockentry",
            name="unit_cost",
            field=models.DecimalField(blank=True, decimal_places=0, default=0, help_text="Cost per unit for stock-in entries.", max_digits=12),
        ),
        migrations.AlterField(
            model_name="stockentry",
            name="entry_type",
            field=models.CharField(
                choices=[
                    ("restock", "Stock In / Restock"),
                    ("sold", "Sold to Customer"),
                    ("service_usage", "Used for Service"),
                    ("damaged", "Damaged"),
                    ("expired", "Expired"),
                    ("lost", "Lost"),
                    ("internal_use", "Internal Use"),
                    ("adjustment", "Adjustment"),
                ],
                db_index=True,
                default="restock",
                max_length=30,
            ),
        ),
        migrations.AlterField(
            model_name="stockentry",
            name="quantity",
            field=models.IntegerField(help_text="Positive adds stock. Negative removes stock."),
        ),
        migrations.AlterField(
            model_name="stockentry",
            name="date",
            field=models.DateField(db_index=True, default=django.utils.timezone.localdate),
        ),
        migrations.CreateModel(
            name="ProductSale",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("quantity", models.PositiveIntegerField(default=1)),
                ("unit_price", models.DecimalField(decimal_places=0, max_digits=12)),
                ("total_amount", models.DecimalField(decimal_places=0, default=0, max_digits=12)),
                ("sale_date", models.DateField(db_index=True, default=django.utils.timezone.localdate)),
                ("notes", models.CharField(blank=True, max_length=255)),
                ("customer", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="product_sales", to="customers.customer")),
                ("product", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="product_sales", to="inventory.product")),
                ("sold_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="product_sales_recorded", to=settings.AUTH_USER_MODEL)),
                ("stock_entry", models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="product_sale", to="inventory.stockentry")),
            ],
            options={
                "ordering": ["-sale_date", "-created_at", "-id"],
            },
        ),
        migrations.AddIndex(
            model_name="product",
            index=models.Index(fields=["category", "product_type"], name="inventory_p_categor_1baf0a_idx"),
        ),
        migrations.AddIndex(
            model_name="product",
            index=models.Index(fields=["is_active"], name="inventory_p_is_acti_68ad4c_idx"),
        ),
        migrations.AddIndex(
            model_name="stockentry",
            index=models.Index(fields=["date", "entry_type"], name="inventory_s_date_3e5438_idx"),
        ),
        migrations.AddIndex(
            model_name="productsale",
            index=models.Index(fields=["sale_date"], name="inventory_p_sale_da_0e2b99_idx"),
        ),
    ]
