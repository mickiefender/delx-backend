from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0004_alter_order_order_id'),
    ]

    operations = [
        migrations.RunSQL(
            sql=(
                "ALTER TABLE orders_order "
                "ALTER COLUMN paystack_reference TYPE varchar(255) "
                "USING paystack_reference::varchar(255);"
            ),
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]
