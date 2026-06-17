from decimal import Decimal

from django.db import migrations, models


def seed_support_commissions(apps, schema_editor):
    Service = apps.get_model("services", "Service")
    for service in Service.objects.all():
        name = (service.name or "").lower()
        price = Decimal(service.price or 0)
        if price == Decimal("20000") and ("haircut" in name or "hair cut" in name):
            service.support_commission_enabled = True
            service.support_commission_amount = Decimal("4000")
            service.save(update_fields=["support_commission_enabled", "support_commission_amount"])
        elif price == Decimal("15000") and ("hair styling" in name or "blow" in name or "curls" in name or "straightening" in name):
            service.support_commission_enabled = True
            service.support_commission_amount = Decimal("2000")
            service.save(update_fields=["support_commission_enabled", "support_commission_amount"])


class Migration(migrations.Migration):
    dependencies = [
        ("services", "0003_service_photo"),
    ]

    operations = [
        migrations.AddField(
            model_name="service",
            name="support_commission_enabled",
            field=models.BooleanField(
                default=False,
                help_text="Enable a fixed support commission for a second employee on this service.",
            ),
        ),
        migrations.AddField(
            model_name="service",
            name="support_commission_amount",
            field=models.DecimalField(
                decimal_places=0,
                default=0,
                help_text="Fixed amount paid to the support employee when this service is approved.",
                max_digits=12,
            ),
        ),
        migrations.RunPython(seed_support_commissions, migrations.RunPython.noop),
    ]
