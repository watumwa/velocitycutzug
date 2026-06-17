from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("expenses", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="expense",
            name="category",
            field=models.CharField(
                choices=[
                    ("rent", "Rent"),
                    ("utilities", "Utilities"),
                    ("electricity", "Electricity"),
                    ("water", "Water"),
                    ("internet", "Internet / Airtime"),
                    ("salaries", "Salaries / Allowances"),
                    ("inventory", "Stock Purchase / Supplies"),
                    ("cleaning", "Cleaning"),
                    ("transport", "Transport"),
                    ("marketing", "Marketing"),
                    ("repairs", "Repairs & Maintenance"),
                    ("equipment", "Equipment Purchase"),
                    ("welfare", "Staff Welfare / Lunch"),
                    ("security", "Security"),
                    ("taxes", "Taxes / Licences"),
                    ("other", "Other"),
                ],
                db_index=True,
                default="other",
                max_length=30,
            ),
        ),
    ]
