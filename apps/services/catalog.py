from decimal import Decimal

from .models import Service

DEFAULT_SERVICE_PRICE = Decimal("0")

SERVICE_CATALOG = (
    (
        "Hair Services",
        (
            "Haircut (men, women, children)",
            "Hair styling (blow-dry, curls, straightening)",
            "Hair coloring (full color, highlights, balayage)",
            "Hair treatments (deep conditioning, keratin, protein treatment)",
            "Hair washing & conditioning",
            "Dreadlocks (installation, retouching, styling)",
            "Braiding (box braids, cornrows, twists)",
            "Wig installation & styling",
            "Relaxing / texturizing",
        ),
    ),
    (
        "Nail Services",
        (
            "Manicure",
            "Pedicure",
            "Gel polish",
            "Acrylic nails",
            "Nail art & design",
            "Nail repair & removal",
        ),
    ),
    (
        "Skin & Beauty Services",
        (
            "Facials (basic, deep cleansing, anti-aging)",
            "Skin treatments (scrubbing, exfoliation)",
            "Makeup (bridal, events, casual)",
            "Eyebrow shaping (threading, waxing)",
            "Eyelash extensions / lifting",
            "Body scrubs",
        ),
    ),
    (
        "Spa & Body Services",
        (
            "Body massage (full body, back, hot stone)",
            "Steam bath / sauna",
            "Body waxing (arms, legs, bikini, full body)",
            "Body polishing",
        ),
    ),
    (
        "Special Packages",
        (
            "Bridal packages",
            "Groom packages",
            "Event styling (photoshoots, parties)",
            "Group bookings",
        ),
    ),
    (
        "Men's Grooming",
        (
            "Beard trimming & shaping",
            "Shaving",
            "Haircuts & fades",
            "Facial treatments for men",
        ),
    ),
)

CATALOG_SERVICE_NAMES = tuple(
    service_name
    for _, service_names in SERVICE_CATALOG
    for service_name in service_names
)
CATALOG_SERVICE_NAME_SET = set(CATALOG_SERVICE_NAMES)


def sync_service_catalog() -> int:
    existing_names = set(
        Service.objects.filter(name__in=CATALOG_SERVICE_NAMES).values_list("name", flat=True)
    )
    missing_names = [
        service_name for service_name in CATALOG_SERVICE_NAMES if service_name not in existing_names
    ]
    Service.objects.bulk_create(
        [
            Service(name=service_name, price=DEFAULT_SERVICE_PRICE, is_active=True)
            for service_name in missing_names
        ]
    )
    return len(missing_names)
