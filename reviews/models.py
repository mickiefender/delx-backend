from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator

from core.supabase_storage import SupabaseStorage


class Review(models.Model):
    """Product reviews"""
    
    product = models.ForeignKey('products.Product', on_delete=models.CASCADE, related_name='reviews')
    user = models.ForeignKey('users.CustomUser', on_delete=models.CASCADE, related_name='reviews')
    order = models.ForeignKey('orders.Order', on_delete=models.SET_NULL, null=True, blank=True, related_name='reviews')
    
    title = models.CharField(max_length=255)
    content = models.TextField()
    rating = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    
    # Review Metadata
    is_verified_purchase = models.BooleanField(default=False)
    helpful_count = models.IntegerField(default=0)
    unhelpful_count = models.IntegerField(default=0)
    is_approved = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        unique_together = ('product', 'user')
        indexes = [
            models.Index(fields=['product', 'rating']),
            models.Index(fields=['is_verified_purchase']),
        ]
    
    def __str__(self):
        return f"Review for {self.product.name} by {self.user.username}"


class ReviewImage(models.Model):
    """Images attached to reviews"""
    
    review = models.ForeignKey(Review, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(
        storage=SupabaseStorage(bucket_name="product-images", folder="reviews"),
        upload_to='',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name_plural = 'Review Images'
    
    def __str__(self):
        return f"Image for review {self.review.id}"


class ReviewResponse(models.Model):
    """Response to a review from product seller/admin"""
    
    review = models.OneToOneField(Review, on_delete=models.CASCADE, related_name='response')
    user = models.ForeignKey('users.CustomUser', on_delete=models.SET_NULL, null=True)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name_plural = 'Review Responses'
    
    def __str__(self):
        return f"Response to review {self.review.id}"
