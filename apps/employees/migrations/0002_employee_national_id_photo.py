import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("employees", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="employee",
            name="national_id",
            field=models.CharField(blank=True, max_length=14, null=True, unique=True),
        ),
        migrations.AddField(
            model_name="employee",
            name="photo",
            field=models.FileField(
                blank=True,
                upload_to="employees/photos/",
                validators=[
                    django.core.validators.FileExtensionValidator(
                        allowed_extensions=["jpg", "jpeg", "png", "webp"]
                    )
                ],
            ),
        ),
    ]
