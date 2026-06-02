import logging
from rest_framework import serializers
from .models import Order, OrderItem, OrderTracking

logger = logging.getLogger(__name__)


class OrderItemSerializer(serializers.ModelSerializer):
    """Serializer for order items"""

    class Meta:
        model = OrderItem
        fields = [
            'id',
            'product',
            'product_name',
            'product_image',
            'sku',
            'price',
            'quantity',
            'subtotal',
            'variant_attributes',
        ]
        # Only id is read-only; subtotal can be passed from frontend for validation.
        # The create method will re-compute subtotal from price * quantity for data integrity.
        read_only_fields = ['id']


class OrderTrackingSerializer(serializers.ModelSerializer):
    """Serializer for order tracking"""
    
    class Meta:
        model = OrderTracking
        fields = ['id', 'status', 'message', 'location', 'timestamp']
        read_only_fields = fields


class OrderListSerializer(serializers.ModelSerializer):
    """Serializer for order list - includes items for display"""
    
    items = OrderItemSerializer(many=True, read_only=True)
    items_count = serializers.SerializerMethodField()
    payment_method = serializers.SerializerMethodField()
    payment_status = serializers.SerializerMethodField()
    
    class Meta:
        model = Order
        fields = [
            'id', 'order_id', 'status', 'subtotal', 'shipping_cost',
            'discount_amount', 'total_amount', 'items_count', 'items',
            'shipping_first_name', 'shipping_last_name', 'shipping_address',
            'shipping_city', 'shipping_state', 'tracking_number',
            'payment_method', 'payment_status',
            'paystack_reference', 'created_at', 'updated_at'
        ]
        read_only_fields = fields
    
    def get_items_count(self, obj):
        return obj.items.count()
    
    def get_payment_method(self, obj):
        """Get payment method from related Payment model"""
        try:
            if hasattr(obj, 'payment') and obj.payment:
                return obj.payment.payment_method
        except Exception:
            pass
        return None
    
    def get_payment_status(self, obj):
        """Get payment status from related Payment model"""
        try:
            if hasattr(obj, 'payment') and obj.payment:
                return obj.payment.status
        except Exception:
            pass
        return None


class OrderDetailSerializer(serializers.ModelSerializer):
    """Serializer for order detail"""
    
    items = OrderItemSerializer(many=True, read_only=True)
    tracking_history = OrderTrackingSerializer(many=True, read_only=True)
    payment_method = serializers.SerializerMethodField()
    payment_status = serializers.SerializerMethodField()
    
    class Meta:
        model = Order
        fields = [
            'id', 'order_id', 'status', 'shipping_first_name', 'shipping_last_name',
            'shipping_email', 'shipping_phone', 'shipping_address', 'shipping_city',
            'shipping_state', 'shipping_postal_code', 'shipping_country',
            'billing_same_as_shipping', 'billing_first_name', 'billing_last_name',
            'billing_address', 'billing_city', 'billing_state', 'billing_postal_code',
            'billing_country', 'subtotal', 'shipping_cost', 'tax_amount',
            'discount_amount', 'coupon_code', 'total_amount', 'notes',
            'tracking_number', 'estimated_delivery', 'items', 'tracking_history',
            'payment_method', 'payment_status',
            'paystack_reference', 'created_at', 'updated_at'
        ]
        read_only_fields = fields
    
    def get_payment_method(self, obj):
        """Get payment method from related Payment model"""
        try:
            if hasattr(obj, 'payment') and obj.payment:
                return obj.payment.payment_method
        except Exception:
            pass
        return None
    
    def get_payment_status(self, obj):
        """Get payment status from related Payment model"""
        try:
            if hasattr(obj, 'payment') and obj.payment:
                return obj.payment.status
        except Exception:
            pass
        return None


class OrderCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating orders"""
    
    items = OrderItemSerializer(many=True, required=True)
    
    # Explicitly define order_id as a CharField to handle custom order IDs from frontend
    order_id = serializers.CharField(max_length=100, required=False, allow_blank=True)

    # Accept money fields from client (optional). If missing, we compute what we can.
    # Use FloatField internally then convert to Decimal for safety with JavaScript numbers
    subtotal = serializers.FloatField(required=False)
    shipping_cost = serializers.FloatField(required=False)
    tax_amount = serializers.FloatField(required=False)
    discount_amount = serializers.FloatField(required=False)
    total_amount = serializers.FloatField(required=False)

    # Shipping fields - allow_blank=True to handle empty strings from frontend
    # The model requires these fields but the frontend may send empty strings
    shipping_first_name = serializers.CharField(max_length=100, required=False, allow_blank=True)
    shipping_last_name = serializers.CharField(max_length=100, required=False, allow_blank=True)
    shipping_email = serializers.EmailField(required=False, allow_blank=True)
    shipping_phone = serializers.CharField(max_length=20, required=False, allow_blank=True)
    shipping_address = serializers.CharField(max_length=255, required=False, allow_blank=True)
    shipping_city = serializers.CharField(max_length=100, required=False, allow_blank=True)
    shipping_state = serializers.CharField(max_length=100, required=False, allow_blank=True)
    shipping_postal_code = serializers.CharField(max_length=20, required=False, allow_blank=True)
    shipping_country = serializers.CharField(max_length=100, required=False, allow_blank=True)

    class Meta:
        model = Order
        fields = [
            # allow client/Paystack to use the same reference as created order
            'order_id',
            'paystack_reference',
            'guest_id',
            # Shipping
            'shipping_first_name', 'shipping_last_name', 'shipping_email',
            'shipping_phone', 'shipping_address', 'shipping_city', 'shipping_state',
            'shipping_postal_code', 'shipping_country',
            # Billing
            'billing_same_as_shipping',
            'billing_first_name', 'billing_last_name', 'billing_address',
            'billing_city', 'billing_state', 'billing_postal_code', 'billing_country',
            # Pricing
            'subtotal', 'shipping_cost', 'tax_amount', 'discount_amount', 'coupon_code', 'total_amount',
            # Order items
            'items', 'notes',
        ]

    def validate_order_id(self, value):
        """Validate and normalize order_id - ensure it's a valid string or generate a new UUID-based one"""
        import uuid
        if not value or str(value).strip() == '':
            # Generate new UUID-based order_id if not provided
            return f"ORD-{uuid.uuid4().hex[:12].upper()}"
        # Ensure it doesn't exceed max_length=100
        value = str(value).strip()[:100]
        return value

    def validate(self, data):
        """Validate data before creating - catch constraint issues early"""
        import logging
        logger = logging.getLogger(__name__)
        
        # Log validation start for debugging
        logger.info(f"OrderCreateSerializer.validate - data keys: {list(data.keys())}")
        
        # Validate order_id length
        order_id = data.get('order_id')
        if order_id and len(order_id) > 100:
            raise serializers.ValidationError({'order_id': 'Order ID cannot exceed 100 characters'})
        
        # Validate paystack_reference length if provided
        paystack_ref = data.get('paystack_reference')
        if paystack_ref and len(str(paystack_ref)) > 255:
            raise serializers.ValidationError({'paystack_reference': 'Reference cannot exceed 255 characters'})
        
        # Validate items
        items = data.get('items')
        if not items:
            raise serializers.ValidationError({'items': 'At least one item is required'})
        
        # Validate each item's decimal fields for precision
        for idx, item in enumerate(items):
            price = item.get('price')
            subtotal = item.get('subtotal')
            
            # Check for None values
            if price is None:
                raise serializers.ValidationError({'items': f'Item {idx}: price is required'})
            if subtotal is None:
                raise serializers.ValidationError({'items': f'Item {idx}: subtotal is required'})
            
            # Validate price precision (max 10 digits, 2 decimal places)
            try:
                price_val = float(price)
                if price_val > 99999999.99:  # max_digits=10, decimal_places=2
                    raise serializers.ValidationError({'items': f'Item {idx}: price value exceeds maximum allowed (99999999.99)'})
            except (TypeError, ValueError):
                raise serializers.ValidationError({'items': f'Item {idx}: invalid price value'})
        
        # Validate money fields for precision
        for field_name in ['subtotal', 'shipping_cost', 'tax_amount', 'discount_amount', 'total_amount']:
            value = data.get(field_name)
            if value is not None:
                try:
                    float_val = float(value)
                    if float_val > 99999999.99:  # max_digits=10, decimal_places=2
                        raise serializers.ValidationError({field_name: f'{field_name} value exceeds maximum allowed (99999999.99)'})
                except (TypeError, ValueError):
                    pass  # Let the FloatField handle validation
        
        logger.info(f"OrderCreateSerializer.validate - passed")
        return super().validate(data)

    def create(self, validated_data):
        from decimal import Decimal, ROUND_HALF_UP
        import logging
        import uuid
        logger = logging.getLogger(__name__)
        
        items_data = validated_data.pop('items')
        
        # Handle order_id: if provided by client, use it; otherwise generate new one
        order_id_value = validated_data.pop('order_id', None)
        if not order_id_value or str(order_id_value).strip() == '':
            order_id_value = f"ORD-{uuid.uuid4().hex[:12].upper()}"
        
        # Log incoming data for debugging
        logger.info(f"OrderCreateSerializer.create - validated_data keys: {validated_data.keys()}")
        logger.info(f"OrderCreateSerializer.create - order_id set to: {order_id_value}")
        logger.info(f"OrderCreateSerializer.create - items_data count: {len(items_data) if items_data else 0}")

        # Safely convert float to Decimal for database - properly quantize to 2 decimal places
        def to_decimal(value, default=0):
            if value is None:
                return Decimal(str(default))
            try:
                # Convert to float then to string to handle JavaScript floating point issues
                float_val = float(value)
                # Round to 2 decimal places and convert to Decimal
                decimal_val = Decimal(str(round(float_val, 2)))
                # Quantize to 2 decimal places to ensure proper decimal_places constraint
                return decimal_val.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            except (TypeError, ValueError) as e:
                logger.error(f"Error converting value to Decimal: {value}, error: {e}")
                return Decimal(str(default))

        # Safely get quantity as integer
        def to_int(value, default=1):
            if value is None:
                return default
            try:
                return int(float(value))
            except (TypeError, ValueError):
                return default

        # Compute subtotal from items (authoritative)
        computed_subtotal = sum(
            to_decimal(item.get('price'), 0) * to_int(item.get('quantity'), 1)
            for item in items_data
        )
        
        logger.info(f"OrderCreateSerializer.create - computed_subtotal: {computed_subtotal}")

        shipping_cost = to_decimal(validated_data.get('shipping_cost'), 0)
        tax_amount = to_decimal(validated_data.get('tax_amount'), 0)
        discount_amount = to_decimal(validated_data.get('discount_amount'), 0)
        
        logger.info(f"OrderCreateSerializer.create - shipping_cost: {shipping_cost}, tax_amount: {tax_amount}, discount_amount: {discount_amount}")

        # Use provided subtotal or fall back to computed
        subtotal = validated_data.get('subtotal')
        if subtotal is not None:
            subtotal = to_decimal(subtotal)
        else:
            subtotal = computed_subtotal

        # Use provided total_amount or compute from components
        total_amount = validated_data.get('total_amount')
        if total_amount is not None:
            total_amount = to_decimal(total_amount)
        else:
            total_amount = subtotal + shipping_cost + tax_amount - discount_amount

        logger.info(f"OrderCreateSerializer.create - final subtotal: {subtotal}, total_amount: {total_amount}")

        order = Order.objects.create(
            **{
                **validated_data,
                'order_id': order_id_value,
                'subtotal': subtotal,
                'shipping_cost': shipping_cost,
                'tax_amount': tax_amount,
                'discount_amount': discount_amount,
                'total_amount': total_amount,
            }
        )

# Ensure product_name/product_image are always available for order items
        # (admin UI depends on these being present).
        from products.models import Product

        for item in items_data:
            price = to_decimal(item.get('price'), 0)
            quantity = to_int(item.get('quantity'), 1)

            logger.info(f"OrderCreateSerializer.create - item: price={price}, quantity={quantity}")

            product = None
            product_value = item.get('product')

            # DRF may pass either a raw PK (int/str), a dictionary with 'id', or an actual Product instance
            if product_value:
                if isinstance(product_value, Product):
                    # Already a Product instance - use it directly
                    product = product_value
                elif isinstance(product_value, dict):
                    # It's a nested representation - extract the ID
                    product_id = product_value.get('id')
                    if product_id:
                        product = Product.objects.filter(id=product_id).first()
                else:
                    # It's a PK (int or str) - query by ID
                    try:
                        product_id = int(product_value)
                        product = Product.objects.filter(id=product_id).first()
                    except (TypeError, ValueError):
                        # If conversion fails, try to get by ID anyway
                        product = Product.objects.filter(id=product_value).first()

            product_name = item.get('product_name')
            product_image = item.get('product_image')

            if (not product_name or str(product_name).strip() == '') and product:
                product_name = getattr(product, 'name', None) or getattr(product, 'product_name', None) or ''

            if (not product_image or str(product_image).strip() == '') and product:
                # Common conventions in this codebase: "image" or "product_image"
                product_image = getattr(product, 'product_image', None) or getattr(product, 'image', None) or ''

            OrderItem.objects.create(
                order=order,
                **{
                    **item,
                    'product_name': product_name,
                    'product_image': product_image,
                    'subtotal': price * quantity,
                },
            )

        return order
