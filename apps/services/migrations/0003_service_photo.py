import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("services", "0002_seed_service_catalog"),
    ]

    operations = [
        migrations.AddField(
            model_name="service",
            name="photo",
            field=models.FileField(
                blank=True,
                upload_to="services/photos/",
                validators=[
                    django.core.validators.FileExtensionValidator(
                        allowed_extensions=["jpg", "jpeg", "png", "webp"]
                    )
                ],
            ),
        ),
    ]
