from rest_framework import serializers
from .models import Payment, Refund


class PaymentSerializer(serializers.ModelSerializer):
    """Serializer for payments"""
    
    order_id = serializers.CharField(source='order.order_id', read_only=True)
    
    class Meta:
        model = Payment
        fields = [
            'id', 'order', 'order_id', 'amount', 'currency', 'payment_method',
            'mobile_provider', 'status', 'is_verified', 'card_last_four',
            'card_brand', 'phone_number', 'paystack_reference', 'created_at'
        ]
        read_only_fields = [
            'id', 'order_id', 'status', 'is_verified', 'card_last_four',
            'card_brand', 'paystack_reference', 'created_at'
        ]


class PaymentInitializeSerializer(serializers.ModelSerializer):
    """Serializer for initializing payments"""

    currency = serializers.CharField(required=False)

    class Meta:
        model = Payment
        fields = [
            'order',
            'amount',
            'currency',
            'payment_method',
            'mobile_provider',
            'card_last_four',
            'card_brand',
            'phone_number',
        ]

    def validate_currency(self, value: str) -> str:
        # Paystack expects standard ISO 4217 codes; normalize Ghana cedis variants to GHS.
        normalized = (value or '').upper().strip()

        # Common client-side mistakes/variants
        if normalized in {'GHS', 'GHC', 'GH¢', 'GH-CEDIS', 'CEDIS'}:
            return 'GHS'

        raise serializers.ValidationError(f'Currency not supported: {normalized}')


class RefundSerializer(serializers.ModelSerializer):
    """Serializer for refunds"""
    
    payment_order_id = serializers.CharField(source='payment.order.order_id', read_only=True)
    
    class Meta:
        model = Refund
        fields = [
            'id', 'payment', 'payment_order_id', 'amount', 'reason', 'description',
            'status', 'refund_reference', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'payment_order_id', 'status', 'refund_reference', 'created_at', 'updated_at'
        ]


class RefundCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating refunds"""
    
    class Meta:
        model = Refund
        fields = ['payment', 'amount', 'reason', 'description']
    
    def validate(self, data):
        payment = data['payment']
        amount = data['amount']
        
        if payment.status != 'success':
            raise serializers.ValidationError('Can only refund successful payments')
        
        if amount > payment.amount:
            raise serializers.ValidationError('Refund amount cannot exceed payment amount')
        
        return data
