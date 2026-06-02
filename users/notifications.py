"""
Notifications model for user notifications.
This handles order updates, promotions, system notifications, etc.
"""
from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class Notification(models.Model):
    """
    User notification model for storing in-app notifications.
    """
    TYPE_ORDER = 'order'
    TYPE_PROMOTION = 'promotion'
    TYPE_SYSTEM = 'system'
    TYPE_WISHLIST = 'wishlist'
    TYPE_REVIEW = 'review'
    TYPE_GENERAL = 'general'
    
    TYPE_CHOICES = [
        (TYPE_ORDER, 'Order'),
        (TYPE_PROMOTION, 'Promotion'),
        (TYPE_SYSTEM, 'System'),
        (TYPE_WISHLIST, 'Wishlist'),
        (TYPE_REVIEW, 'Review'),
        (TYPE_GENERAL, 'General'),
    ]
    
    user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='notifications'
    )
    title = models.CharField(max_length=255)
    message = models.TextField()
    type = models.CharField(max_length=20, choices=TYPE_CHOICES, default=TYPE_GENERAL)
    is_read = models.BooleanField(default=False)
    
    # Optional: reference to related objects
    order_id = models.CharField(max_length=50, blank=True, null=True)
    product_id = models.IntegerField(blank=True, null=True)
    
    # Additional data as JSON
    data = models.JSONField(blank=True, null=True, default=dict)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Notification'
        verbose_name_plural = 'Notifications'
        indexes = [
            models.Index(fields=['user', 'is_read']),
            models.Index(fields=['user', 'created_at']),
        ]
    
    def __str__(self):
        return f"{self.user.email} - {self.title[:30]}"
