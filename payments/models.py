from django.db import models


class Payment(models.Model):
    """Payment model"""
    
    METHOD_CHOICES = (
        ('card', 'Credit/Debit Card'),
        ('mobile_money', 'Mobile Money'),
        ('bank_transfer', 'Bank Transfer'),
        ('paypal', 'PayPal'),
    )
    
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('success', 'Success'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
    )
    
    MOBILE_PROVIDER_CHOICES = (
        ('mtn', 'MTN MoMo'),
        ('telecel', 'Telecel Cash'),
        ('airteltigo', 'AirtelTigo Money'),
    )
    
    order = models.OneToOneField('orders.Order', on_delete=models.CASCADE, related_name='payment', null=True, blank=True)
    user = models.ForeignKey('users.CustomUser', on_delete=models.SET_NULL, null=True, related_name='payments')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default='GHS')
    payment_method = models.CharField(max_length=20, choices=METHOD_CHOICES)
    mobile_provider = models.CharField(max_length=20, choices=MOBILE_PROVIDER_CHOICES, blank=True, null=True)
    
    # Paystack Info
    paystack_reference = models.CharField(max_length=255, unique=True, blank=True, null=True)
    paystack_authorization_url = models.URLField(blank=True, null=True)
    paystack_access_code = models.CharField(max_length=255, blank=True, null=True)
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    is_verified = models.BooleanField(default=False)
    
    # Card Info (stored securely, never store full details)
    card_last_four = models.CharField(max_length=4, blank=True)
    card_brand = models.CharField(max_length=50, blank=True)
    
    # Phone Info (for mobile money)
    phone_number = models.CharField(max_length=20, blank=True)
    
    # Bank Info
    bank_name = models.CharField(max_length=255, blank=True)
    bank_account = models.CharField(max_length=100, blank=True)
    
    # Response Data
    response_data = models.JSONField(default=dict, blank=True)
    error_message = models.TextField(blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['order']),
            models.Index(fields=['user']),
            models.Index(fields=['status']),
            models.Index(fields=['paystack_reference']),
        ]
    
    def __str__(self):
        return f"Payment for Order {self.order.order_id}"


class Refund(models.Model):
    """Refund model"""
    
    REASON_CHOICES = (
        ('customer_request', 'Customer Request'),
        ('payment_error', 'Payment Error'),
        ('item_unavailable', 'Item Unavailable'),
        ('wrong_item', 'Wrong Item Shipped'),
        ('damaged_item', 'Damaged Item'),
        ('order_cancellation', 'Order Cancellation'),
    )
    
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('processed', 'Processed'),
    )
    
    payment = models.ForeignKey(Payment, on_delete=models.CASCADE, related_name='refunds')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    reason = models.CharField(max_length=50, choices=REASON_CHOICES)
    description = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    refund_reference = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Refund for {self.payment.order.order_id}"
