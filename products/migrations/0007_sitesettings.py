from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("products", "0006_productattribute_product_attributes"),
    ]

    operations = [
        migrations.CreateModel(
            name="SiteSettings",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("site_name", models.CharField(default="Delchris E-Commerce", max_length=200)),
                ("site_description", models.TextField(blank=True, default="")),
                ("primary_color", models.CharField(default="#2E7D32", max_length=20)),
                ("secondary_color", models.CharField(default="#C62828", max_length=20)),
                ("accent_color", models.CharField(default="#F57C00", max_length=20)),
                ("contact_email", models.EmailField(blank=True, default="")),
                ("contact_phone", models.CharField(blank=True, default="", max_length=50)),
                ("contact_address", models.TextField(blank=True, default="")),
                ("facebook_url", models.URLField(blank=True, default="")),
                ("instagram_url", models.URLField(blank=True, default="")),
                ("twitter_url", models.URLField(blank=True, default="")),
                ("whatsapp_number", models.CharField(blank=True, default="", max_length=50)),
                ("free_shipping_threshold", models.DecimalField(decimal_places=2, default=500, max_digits=10)),
                ("shipping_flat_rate", models.DecimalField(decimal_places=2, default=15, max_digits=10)),
                ("local_shipping_rate", models.DecimalField(decimal_places=2, default=10, max_digits=10)),
                ("return_policy_days", models.IntegerField(default=7)),
                ("return_policy_text", models.TextField(blank=True, default="")),
                ("site_logo", models.ImageField(blank=True, null=True, upload_to="settings/")),
                ("favicon", models.ImageField(blank=True, null=True, upload_to="settings/")),
                ("is_maintenance_mode", models.BooleanField(default=False)),
                ("maintenance_message", models.TextField(blank=True, default="")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "Site Settings",
                "verbose_name_plural": "Site Settings",
            },
        ),
    ]
