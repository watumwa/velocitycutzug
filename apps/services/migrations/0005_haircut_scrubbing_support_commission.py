from decimal import Decimal

from django.db import migrations


def enable_haircut_scrubbing_support(apps, schema_editor):
    Service = apps.get_model("services", "Service")
    for service in Service.objects.filter(price=Decimal("15000")):
        name = (service.name or "").lower()
        if "haircut" in name or "hair cut" in name or "fade" in name:
            service.support_commission_enabled = True
            service.support_commission_amount = Decimal("2000")
            service.save(update_fields=["support_commission_enabled", "support_commission_amount"])


class Migration(migrations.Migration):
    dependencies = [
        ("services", "0004_support_commission_fields"),
    ]

    operations = [
        migrations.RunPython(enable_haircut_scrubbing_support, migrations.RunPython.noop),
    ]
