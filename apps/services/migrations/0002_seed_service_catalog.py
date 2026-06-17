from decimal import Decimal

from django.db import migrations

SERVICE_NAMES = (
    "Haircut (men, women, children)",
    "Hair styling (blow-dry, curls, straightening)",
    "Hair coloring (full color, highlights, balayage)",
    "Hair treatments (deep conditioning, keratin, protein treatment)",
    "Hair washing & conditioning",
    "Dreadlocks (installation, retouching, styling)",
    "Braiding (box braids, cornrows, twists)",
    "Wig installation & styling",
    "Relaxing / texturizing",
    "Manicure",
    "Pedicure",
    "Gel polish",
    "Acrylic nails",
    "Nail art & design",
    "Nail repair & removal",
    "Facials (basic, deep cleansing, anti-aging)",
    "Skin treatments (scrubbing, exfoliation)",
    "Makeup (bridal, events, casual)",
    "Eyebrow shaping (threading, waxing)",
    "Eyelash extensions / lifting",
    "Body scrubs",
    "Body massage (full body, back, hot stone)",
    "Steam bath / sauna",
    "Body waxing (arms, legs, bikini, full body)",
    "Body polishing",
    "Bridal packages",
    "Groom packages",
    "Event styling (photoshoots, parties)",
    "Group bookings",
    "Beard trimming & shaping",
    "Shaving",
    "Haircuts & fades",
    "Facial treatments for men",
)


def seed_service_catalog(apps, schema_editor):
    Service = apps.get_model("services", "Service")
    existing_names = set(Service.objects.filter(name__in=SERVICE_NAMES).values_list("name", flat=True))
    Service.objects.bulk_create(
        [
            Service(name=service_name, price=Decimal("0"), is_active=True)
            for service_name in SERVICE_NAMES
            if service_name not in existing_names
        ]
    )


class Migration(migrations.Migration):

    dependencies = [
        ("services", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed_service_catalog, migrations.RunPython.noop),
    ]
