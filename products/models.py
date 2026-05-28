import random
import string

from django.db import models
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils.text import slugify

from core.supabase_storage import SupabaseStorage


class Category(models.Model):
    """Product categories"""
    
    name = models.CharField(max_length=200, unique=True)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True, null=True)
    image = models.ImageField(
        storage=SupabaseStorage(bucket_name="product-images", folder="categories"),
        upload_to='',
        blank=True,
        null=True,
    )
    is_active = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['name']
        verbose_name_plural = 'Categories'
    
    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class Brand(models.Model):
    """Product brands (for homepage/products filtering + logos)"""
    name = models.CharField(max_length=200, unique=True)
    slug = models.SlugField(unique=True)
    logo = models.ImageField(
        storage=SupabaseStorage(bucket_name="product-images", folder="brands"),
        upload_to='',
        blank=True,
        null=True,
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        verbose_name_plural = 'Brands'

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class Product(models.Model):
    """Product model"""
    
    STATUS_CHOICES = (
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('discontinued', 'Discontinued'),
    )

    COLLECTION_CHOICES = (
        ('none', 'None'),
        ('new_arrival', 'New Arrival'),
        ('best_seller', 'Best Seller'),
        ('special_offer', 'Special Offer'),
    )
    
    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, related_name='products')
    brand = models.ForeignKey('Brand', on_delete=models.SET_NULL, null=True, blank=True, related_name='products')
    description = models.TextField()
    short_description = models.CharField(max_length=500, blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    original_price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    sku = models.CharField(max_length=100, unique=True)
    stock_quantity = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    is_featured = models.BooleanField(default=False)
    collection = models.CharField(max_length=30, choices=COLLECTION_CHOICES, default='none')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    image = models.ImageField(
        storage=SupabaseStorage(bucket_name="product-images", folder="products"),
        upload_to='',
    )
    rating = models.DecimalField(max_digits=3, decimal_places=2, default=0, validators=[MinValueValidator(0), MaxValueValidator(5)])
    review_count = models.IntegerField(default=0)
    created_by = models.ForeignKey('users.CustomUser', on_delete=models.SET_NULL, null=True, blank=True)
    attributes = models.ManyToManyField('ProductAttribute', blank=True, related_name='products', help_text="Product attributes")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['slug']),
            models.Index(fields=['category']),
            models.Index(fields=['status']),
        ]
    
    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)

        if not self.sku:
            base = slugify(self.name).replace('-', '').upper()[:8] or 'PRD'
            while True:
                suffix = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
                candidate = f"{base}-{suffix}"
                if not Product.objects.filter(sku=candidate).exclude(pk=self.pk).exists():
                    self.sku = candidate
                    break

        super().save(*args, **kwargs)
    
    @property
    def discount_percentage(self):
        if self.original_price and self.original_price > self.price:
            return round(((self.original_price - self.price) / self.original_price) * 100)
        return 0
    
    @property
    def is_in_stock(self):
        return self.stock_quantity > 0


class ProductImage(models.Model):
    """Additional product images"""
    
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(
        storage=SupabaseStorage(bucket_name="product-images", folder="products"),
        upload_to='',
    )
    alt_text = models.CharField(max_length=255, blank=True)
    is_primary = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['order', 'created_at']
        verbose_name_plural = 'Product Images'
    
    def __str__(self):
        return f"Image for {self.product.name}"


class ProductVariant(models.Model):
    """Product variants (size, color, etc)"""
    
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='variants')
    name = models.CharField(max_length=255)
    sku = models.CharField(max_length=100, unique=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    stock_quantity = models.IntegerField(default=0)
    attributes = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['name']
    
    def __str__(self):
        return f"{self.product.name} - {self.name}"


class ProductAttribute(models.Model):
    """Product attributes that can be assigned to products (e.g., Color, Size, Material)"""
    
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(unique=True)
    values = models.JSONField(default=list, help_text="List of possible values, e.g., ['Red', 'Blue', 'Green']")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['name']
        verbose_name_plural = 'Product Attributes'
    
    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class HeroBanner(models.Model):
    """Hero banner displayed on the homepage (public) and managed in admin (staff)."""

    # Basic content
    title = models.CharField(max_length=200, blank=True, default='')
    subtitle = models.CharField(max_length=300, blank=True, default='')
    cta_text = models.CharField(max_length=120, blank=True, default='')
    cta_url = models.URLField(blank=True, default='')

    # Media
    image = models.ImageField(
        storage=SupabaseStorage(bucket_name="product-images", folder="hero-banners"),
        upload_to='',
        max_length=500,
        blank=True,
        null=True,
    )

    # Rotation / visibility
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0, db_index=True)

    # Auto-rotation (seconds)
    duration_seconds = models.PositiveIntegerField(default=6)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['sort_order', 'created_at']
        verbose_name_plural = 'Hero Banners'

    def __str__(self):
        return f"HeroBanner({self.title or 'Untitled'})"


class HomeAdBanner(models.Model):
    """
    Two-image ads block for the homepage (uploaded via admin dashboard).
    Position 1/2 corresponds to left/right (or first/second) banner.
    """
    POSITION_CHOICES = (
        (1, 'Left/First'),
        (2, 'Right/Second'),
    )

    position = models.PositiveSmallIntegerField(choices=POSITION_CHOICES, unique=True, db_index=True)
    image = models.ImageField(
        storage=SupabaseStorage(bucket_name="product-images", folder="home-ads"),
        upload_to='',
        max_length=500,
        blank=True,
        null=True,
    )
    link_url = models.URLField(blank=True, default='')
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['position']
        verbose_name = "Home Ad Banner"
        verbose_name_plural = "Home Ad Banners"

    def __str__(self):
        return f"HomeAdBanner(position={self.position})"


class SiteSettings(models.Model):
    """
    Site settings model for storing website configuration.
    This model uses singleton pattern - only one instance should exist.
    """
    
    # Site Information
    site_name = models.CharField(max_length=200, default='Delchris E-Commerce')
    site_description = models.TextField(blank=True, default='')
    
    # Theme Colors (stored as hex values)
    primary_color = models.CharField(max_length=20, default='#2E7D32')  # Green
    secondary_color = models.CharField(max_length=20, default='#C62828')   # Red
    accent_color = models.CharField(max_length=20, default='#F57C00')     # Orange
    
    # Contact Information
    contact_email = models.EmailField(blank=True, default='')
    contact_phone = models.CharField(max_length=50, blank=True, default='')
    contact_address = models.TextField(blank=True, default='')
    
    # Social Media Links
    facebook_url = models.URLField(blank=True, default='')
    instagram_url = models.URLField(blank=True, default='')
    twitter_url = models.URLField(blank=True, default='')
    whatsapp_number = models.CharField(max_length=50, blank=True, default='')
    
# Shipping Settings
    free_shipping_threshold = models.DecimalField(max_digits=10, decimal_places=2, default=500)
    shipping_flat_rate = models.DecimalField(max_digits=10, decimal_places=2, default=15)
    local_shipping_rate = models.DecimalField(max_digits=10, decimal_places=2, default=10)
    
    # Tax Settings (e.g. 0 = 0%, 0.15 = 15%)
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    
    # Return Policy
    return_policy_days = models.IntegerField(default=7)
    return_policy_text = models.TextField(blank=True, default='')
    
    # Logo and Media
    site_logo = models.ImageField(
        storage=SupabaseStorage(bucket_name="product-images", folder="settings"),
        upload_to='',
        max_length=500,
        blank=True,
        null=True,
    )
    favicon = models.ImageField(
        storage=SupabaseStorage(bucket_name="product-images", folder="settings"),
        upload_to='',
        max_length=500,
        blank=True,
        null=True,
    )
    
    # Maintenance Mode
    is_maintenance_mode = models.BooleanField(default=False)
    maintenance_message = models.TextField(blank=True, default='')
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Site Settings'
        verbose_name_plural = 'Site Settings'
    
    def __str__(self):
        return f"Site Settings - {self.site_name}"
    
    def save(self, *args, **kwargs):
        # Ensure only one instance exists
        if not self.pk and SiteSettings.objects.exists():
            raise ValidationError("Only one set of site settings is allowed.")
        super().save(*args, **kwargs)
