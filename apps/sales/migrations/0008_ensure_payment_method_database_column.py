# Generated manually to repair a state/database mismatch from 0006.

from django.db import migrations


def ensure_payment_method_column(apps, schema_editor):
    table_name = "sales_sale"
    column_name = "payment_method"
    connection = schema_editor.connection

    existing_columns = {
        column.name
        for column in connection.introspection.get_table_description(
            schema_editor.connection.cursor(),
            table_name,
        )
    }
    if column_name in existing_columns:
        return

    schema_editor.execute(
        f"ALTER TABLE {schema_editor.quote_name(table_name)} "
        f"ADD COLUMN {schema_editor.quote_name(column_name)} varchar(20) NOT NULL DEFAULT 'cash'"
    )


class Migration(migrations.Migration):
    dependencies = [
        ("sales", "0007_rename_sales_sale_status__3e0b1d_idx_sales_sale_status_89a0f1_idx_and_more"),
    ]

    operations = [
        migrations.RunPython(ensure_payment_method_column, migrations.RunPython.noop),
    ]
