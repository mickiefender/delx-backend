from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0003_add_paystack_reference'),
    ]

    operations = [
        migrations.RunSQL(
            sql=(
                "ALTER TABLE orders_order "
                "ALTER COLUMN order_id TYPE varchar(100) "
                "USING order_id::varchar(100);"
            ),
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]
