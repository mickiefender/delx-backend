from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.conf import settings
import secrets
import hashlib

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


class PasswordResetToken(models.Model):
    """Token for password reset functionality"""
    
    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='password_reset_tokens'
    )
    token = models.CharField(max_length=64, unique=True, db_index=True)
    token_hash = models.CharField(max_length=64, unique=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    used = models.BooleanField(default=False)
    used_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Password Reset Token'
        verbose_name_plural = 'Password Reset Tokens'
    
    def __str__(self):
        return f"Password reset for {self.user.email}"
    
    @classmethod
    def create_token(cls, user):
        """Create a new password reset token for a user"""
        # Generate a secure random token
        token = secrets.token_urlsafe(32)
        
        # Create hash for storage (so token can't be recovered from DB)
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        
        # Get expiration from settings or default to 24 hours
        from django.conf import settings
        token_lifetime = getattr(settings, 'PASSWORD_RESET_TOKEN_LIFETIME', 24)  # hours
        
        expires_at = timezone.now() + timezone.timedelta(hours=token_lifetime)
        
        # Delete any existing unused tokens for this user
        cls.objects.filter(user=user, used=False).delete()
        
        # Create new token
        reset_token = cls.objects.create(
            user=user,
            token=token,
            token_hash=token_hash,
            expires_at=expires_at
        )
        
        return reset_token
    
    def is_valid(self):
        """Check if token is valid (not used and not expired)"""
        return (
            not self.used and
            timezone.now() < self.expires_at
        )
    
    def mark_used(self):
        """Mark token as used"""
        self.used = True
        self.used_at = timezone.now()
        self.save(update_fields=['used', 'used_at'])


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


class DeviceToken(models.Model):
    """
    Stores a user's push notification device token (FCM).
    Used for sending order/shipping updates.
    """

    PLATFORM_ANDROID = 'android'
    PLATFORM_IOS = 'ios'
    PLATFORM_CHOICES = (
        (PLATFORM_ANDROID, 'Android'),
        (PLATFORM_IOS, 'iOS'),
    )

    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='device_tokens')
    platform = models.CharField(max_length=10, choices=PLATFORM_CHOICES)
    token = models.TextField(unique=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    last_seen_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = 'Device Token'
        verbose_name_plural = 'Device Tokens'
        indexes = [
            models.Index(fields=['user']),
            models.Index(fields=['platform']),
        ]

def __str__(self):
        return f"DeviceToken(user_id={self.user_id}, platform={self.platform})"


# Import Notification model from notifications.py
from .notifications import Notification
