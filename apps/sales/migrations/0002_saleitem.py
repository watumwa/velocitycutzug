from django.db import migrations, models
import django.db.models.deletion


def backfill_sale_items(apps, schema_editor):
    Sale = apps.get_model("sales", "Sale")
    SaleItem = apps.get_model("sales", "SaleItem")

    existing_sale_ids = set(SaleItem.objects.values_list("sale_id", flat=True))
    items_to_create = []

    for sale in Sale.objects.all():
        if sale.id in existing_sale_ids:
            continue
        items_to_create.append(
            SaleItem(
                sale_id=sale.id,
                service_id=sale.service_id,
                price=sale.amount,
            )
        )

    SaleItem.objects.bulk_create(items_to_create)


class Migration(migrations.Migration):

    dependencies = [
        ("services", "0002_seed_service_catalog"),
        ("sales", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="SaleItem",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("price", models.DecimalField(decimal_places=0, max_digits=12)),
                (
                    "sale",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="items", to="sales.sale"),
                ),
                (
                    "service",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="sale_items",
                        to="services.service",
                    ),
                ),
            ],
            options={
                "ordering": ["id"],
                "constraints": [
                    models.UniqueConstraint(fields=("sale", "service"), name="unique_sale_service_item")
                ],
            },
        ),
        migrations.RunPython(backfill_sale_items, migrations.RunPython.noop),
    ]
