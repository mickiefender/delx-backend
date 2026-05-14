from rest_framework import serializers
from .models import Order, OrderItem, OrderTracking


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
        # Only subtotal is derived in OrderCreateSerializer; name/image come from payload.
        read_only_fields = ['id', 'subtotal']


class OrderTrackingSerializer(serializers.ModelSerializer):
    """Serializer for order tracking"""
    
    class Meta:
        model = OrderTracking
        fields = ['id', 'status', 'message', 'location', 'timestamp']
        read_only_fields = fields


class OrderListSerializer(serializers.ModelSerializer):
    """Serializer for order list"""
    
    items_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Order
        fields = [
            'id', 'order_id', 'status', 'total_amount', 'items_count',
            'created_at', 'updated_at'
        ]
        read_only_fields = fields
    
    def get_items_count(self, obj):
        return obj.items.count()


class OrderDetailSerializer(serializers.ModelSerializer):
    """Serializer for order detail"""
    
    items = OrderItemSerializer(many=True, read_only=True)
    tracking_history = OrderTrackingSerializer(many=True, read_only=True)
    
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
            'created_at', 'updated_at'
        ]
        read_only_fields = fields


class OrderCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating orders"""
    
    items = OrderItemSerializer(many=True, required=True)

    # Accept money fields from client (optional). If missing, we compute what we can.
    subtotal = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)
    shipping_cost = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)
    tax_amount = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)
    discount_amount = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)
    total_amount = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)

    class Meta:
        model = Order
        fields = [
            # allow client/Paystack to use the same reference as created order
            'order_id',
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

    def create(self, validated_data):
        items_data = validated_data.pop('items')

        # Compute subtotal from items (authoritative)
        computed_subtotal = sum(
            (item.get('price') or 0) * (item.get('quantity') or 1)
            for item in items_data
        )

        shipping_cost = validated_data.get('shipping_cost') or 0
        tax_amount = validated_data.get('tax_amount') or 0
        discount_amount = validated_data.get('discount_amount') or 0

        subtotal = validated_data.get('subtotal') or computed_subtotal
        # Prefer computed_subtotal if provided subtotal is inconsistent/missing
        if subtotal != computed_subtotal:
            subtotal = computed_subtotal

        total_amount = validated_data.get('total_amount')
        if total_amount is None:
            total_amount = subtotal + shipping_cost + tax_amount - discount_amount

        order = Order.objects.create(
            **{
                **validated_data,
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
            price = item.get('price') or 0
            quantity = item.get('quantity') or 1

            product = None
            product_id = item.get('product')
            if product_id:
                product = Product.objects.filter(id=product_id).first()

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
