from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils.translation import gettext_lazy as _

from core.supabase_storage import SupabaseStorage


class CustomUser(AbstractUser):
    """Extended user model with additional fields for ecommerce"""
    
    GENDER_CHOICES = (
        ('M', 'Male'),
        ('F', 'Female'),
        ('O', 'Other'),
    )
    
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    profile_image = models.ImageField(
        storage=SupabaseStorage(bucket_name="product-images", folder="users"),
        upload_to='',
        blank=True,
        null=True,
    )
    bio = models.TextField(blank=True, null=True)
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES, blank=True)
    date_of_birth = models.DateField(blank=True, null=True)
    is_verified = models.BooleanField(default=False)
    preferred_currency = models.CharField(max_length=3, default='GHS')
    preferred_language = models.CharField(max_length=5, default='en')
    newsletter_subscribed = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = _('User')
        verbose_name_plural = _('Users')
    
    def __str__(self):
        return f"{self.get_full_name()} ({self.email})"


class UserAddress(models.Model):
    """User shipping and billing addresses"""
    
    ADDRESS_TYPE_CHOICES = (
        ('shipping', 'Shipping Address'),
        ('billing', 'Billing Address'),
        ('both', 'Both'),
    )
    
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='addresses')
    address_type = models.CharField(max_length=10, choices=ADDRESS_TYPE_CHOICES, default='shipping')
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    phone_number = models.CharField(max_length=20)
    email = models.EmailField()
    street_address = models.CharField(max_length=255)
    city = models.CharField(max_length=100)
    state_province = models.CharField(max_length=100)
    postal_code = models.CharField(max_length=20)
    country = models.CharField(max_length=100)
    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-is_default', '-created_at']
        verbose_name_plural = 'User Addresses'
    
    def __str__(self):
        return f"{self.first_name} {self.last_name} - {self.street_address}, {self.city}"


class UserWishlist(models.Model):
    """User wishlist/favorites"""
    
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='wishlist')
    products = models.ManyToManyField('products.Product', related_name='wishlisted_by', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name_plural = 'User Wishlists'
    
    def __str__(self):
        return f"{self.user.username}'s Wishlist"
