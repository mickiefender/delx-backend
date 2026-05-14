from django.db import models
from django.utils import timezone


class SalesMetric(models.Model):
    """Track sales metrics"""
    
    date = models.DateField(db_index=True)
    total_orders = models.IntegerField(default=0)
    total_sales = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_revenue = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    average_order_value = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    unique_customers = models.IntegerField(default=0)
    
    class Meta:
        ordering = ['-date']
        unique_together = ('date',)
    
    def __str__(self):
        return f"Sales for {self.date}"


class ProductMetric(models.Model):
    """Track product performance"""
    
    product = models.ForeignKey('products.Product', on_delete=models.CASCADE, related_name='metrics')
    date = models.DateField(db_index=True)
    views = models.IntegerField(default=0)
    clicks = models.IntegerField(default=0)
    sales = models.IntegerField(default=0)
    revenue = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    conversion_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    
    class Meta:
        ordering = ['-date']
        unique_together = ('product', 'date')
    
    def __str__(self):
        return f"{self.product.name} metrics for {self.date}"


class UserMetric(models.Model):
    """Track user activity"""
    
    date = models.DateField(db_index=True)
    new_registrations = models.IntegerField(default=0)
    active_users = models.IntegerField(default=0)
    returning_users = models.IntegerField(default=0)
    abandoned_carts = models.IntegerField(default=0)
    abandoned_cart_value = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    class Meta:
        ordering = ['-date']
        unique_together = ('date',)
    
    def __str__(self):
        return f"User metrics for {self.date}"


class CategoryMetric(models.Model):
    """Track category performance"""
    
    category = models.ForeignKey('products.Category', on_delete=models.CASCADE, related_name='metrics')
    date = models.DateField(db_index=True)
    views = models.IntegerField(default=0)
    sales = models.IntegerField(default=0)
    revenue = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    class Meta:
        ordering = ['-date']
        unique_together = ('category', 'date')
        verbose_name_plural = 'Category Metrics'
    
    def __str__(self):
        return f"{self.category.name} metrics for {self.date}"


class PageView(models.Model):
    """Track page views"""
    
    page_name = models.CharField(max_length=255, db_index=True)
    page_path = models.CharField(max_length=500)
    user = models.ForeignKey('users.CustomUser', on_delete=models.SET_NULL, null=True, blank=True)
    session_id = models.CharField(max_length=255, blank=True)
    referrer = models.URLField(blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True, db_index=True)
    device = models.CharField(max_length=50, blank=True)
    browser = models.CharField(max_length=50, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    
    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['page_name', '-timestamp']),
            models.Index(fields=['user', '-timestamp']),
        ]
    
    def __str__(self):
        return f"View of {self.page_name} at {self.timestamp}"


class ClickEvent(models.Model):
    """
    Track site-wide click events (buttons/links) for analytics dashboards.
    """
    page_path = models.CharField(max_length=500, db_index=True)
    session_id = models.CharField(max_length=255, blank=True, db_index=True)
    user = models.ForeignKey('users.CustomUser', on_delete=models.SET_NULL, null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True, db_index=True)
    device = models.CharField(max_length=50, blank=True)
    browser = models.CharField(max_length=50, blank=True)
    element_label = models.CharField(max_length=255, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['page_path', '-timestamp']),
        ]

    def __str__(self):
        return f"Click on {self.page_path} at {self.timestamp}"


class AbandonedCart(models.Model):
    """Track abandoned carts"""
    
    user = models.ForeignKey('users.CustomUser', on_delete=models.CASCADE, related_name='abandoned_carts')
    items_data = models.JSONField()
    total_value = models.DecimalField(max_digits=10, decimal_places=2)
    recovery_email_sent = models.BooleanField(default=False)
    recovery_email_sent_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Abandoned cart for {self.user.username} - {self.total_value}"
