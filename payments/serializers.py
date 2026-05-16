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


class PaymentInitializeSerializer(serializers.Serializer):
    """
    Serializer for initializing payments (matches frontend payload)

    Frontend sends:
    - email
    - amount
    - orderId
    - phone
    - paymentMethod: 'card'|'mobile_money'|'bank_transfer'
    - mobileMoneyProvider?: 'mtn'|'telecel'|'airteltigo'
    """
    email = serializers.EmailField()
    amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    orderId = serializers.CharField(max_length=100)
    phone = serializers.CharField(max_length=20, allow_blank=True, required=False)

    paymentMethod = serializers.ChoiceField(choices=['card', 'mobile_money', 'bank_transfer'])
    mobileMoneyProvider = serializers.ChoiceField(
        choices=['mtn', 'telecel', 'airteltigo'],
        required=False,
        allow_null=True,
    )

    currency = serializers.CharField(required=False)

    def validate_currency(self, value: str) -> str:
        normalized = (value or '').upper().strip()
        if normalized in {'GHS', 'GHC', 'GH¢', 'GH-CEDIS', 'CEDIS'}:
            return 'GHS'
        raise serializers.ValidationError(f'Currency not supported: {normalized}')

    def create(self, validated_data):
        """
        Create Payment instance. ViewSet will set user/status and call Paystack.
        """
        from orders.models import Order  # local import to avoid circulars

        order = Order.objects.get(order_id=validated_data['orderId'])

        payment = Payment(
            order=order,
            amount=validated_data['amount'],
            currency=validated_data.get('currency') or 'GHS',
            payment_method=validated_data['paymentMethod'],
            mobile_provider=validated_data.get('mobileMoneyProvider'),
            phone_number=validated_data.get('phone') or '',
            status='pending',
        )
        return payment


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
