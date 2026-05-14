from rest_framework import serializers
from .models import Category, Brand, Product, ProductImage, ProductVariant, ProductAttribute, HeroBanner, HomeAdBanner, SiteSettings


class CategorySerializer(serializers.ModelSerializer):
    """Serializer for categories"""
    
    class Meta:
        model = Category
        fields = ['id', 'name', 'slug', 'description', 'image', 'is_active', 'is_featured', 'created_at']
        read_only_fields = ['id', 'slug', 'created_at']


class BrandSerializer(serializers.ModelSerializer):
    """Serializer for brands (public)"""

    class Meta:
        model = Brand
        fields = ['id', 'name', 'slug', 'logo', 'is_active', 'created_at']
        read_only_fields = ['id', 'slug', 'created_at']

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        if instance.logo:
            ret['logo'] = instance.logo.url
        else:
            ret['logo'] = None
        return ret


class ProductImageSerializer(serializers.ModelSerializer):
    """Serializer for product images"""
    
    class Meta:
        model = ProductImage
        fields = ['id', 'image', 'alt_text', 'is_primary', 'order']
        read_only_fields = ['id']


class ProductVariantSerializer(serializers.ModelSerializer):
    """Serializer for product variants"""
    
    class Meta:
        model = ProductVariant
        fields = ['id', 'name', 'sku', 'price', 'stock_quantity', 'attributes']
        read_only_fields = ['id']


class ProductAttributeSerializer(serializers.ModelSerializer):
    """Serializer for product attributes"""
    
    class Meta:
        model = ProductAttribute
        fields = ['id', 'name', 'slug', 'values', 'is_active', 'created_at']
        read_only_fields = ['id', 'slug', 'created_at']


class ProductListSerializer(serializers.ModelSerializer):
    """Serializer for product list"""
    
    category_name = serializers.CharField(source='category.name', read_only=True)
    brand_name = serializers.CharField(source='brand.name', read_only=True)
    brand = serializers.IntegerField(source='brand.id', allow_null=True, required=False)
    discount_percentage = serializers.SerializerMethodField()
    
    class Meta:
        model = Product
        fields = [
            'id',
            'name',
            'slug',
            'category',
            'category_name',
            'brand',
            'brand_name',
            'price',
            'original_price',
            'image',
            'rating',
            'review_count',
            'discount_percentage',
            'is_featured',
            'collection',
            'stock_quantity',
            'is_in_stock',
        ]
        read_only_fields = fields
    
    def get_discount_percentage(self, obj):
        return obj.discount_percentage


class ProductDetailSerializer(serializers.ModelSerializer):
    """Serializer for product detail"""
    
    category_name = serializers.CharField(source='category.name', read_only=True)
    brand_name = serializers.CharField(source='brand.name', read_only=True)
    brand = serializers.IntegerField(source='brand.id', allow_null=True, required=False)
    images = ProductImageSerializer(many=True, read_only=True)
    variants = ProductVariantSerializer(many=True, read_only=True)
    attributes = ProductAttributeSerializer(many=True, read_only=True)
    discount_percentage = serializers.SerializerMethodField()
    reviews = serializers.SerializerMethodField()
    
    class Meta:
        model = Product
        fields = [
            'id',
            'name',
            'slug',
            'category',
            'category_name',
            'brand',
            'brand_name',
            'description',
            'short_description',
            'price',
            'original_price',
            'sku',
            'stock_quantity',
            'is_featured',
            'collection',
            'status',
            'image',
            'images',
            'variants',
            'attributes',
            'rating',
            'review_count',
            'discount_percentage',
            'reviews',
            'created_at',
            'updated_at',
        ]
        read_only_fields = fields
    
    def get_discount_percentage(self, obj):
        return obj.discount_percentage
    
    def get_reviews(self, obj):
        from reviews.serializers import ReviewListSerializer
        reviews = obj.reviews.filter(is_approved=True)[:5]
        return ReviewListSerializer(reviews, many=True).data


class ProductCreateUpdateSerializer(serializers.ModelSerializer):
    """Serializer for creating/updating products"""
    
    additional_images = serializers.ListField(
        child=serializers.ImageField(),
        write_only=True,
        required=False
    )
    sku = serializers.CharField(required=False, allow_blank=True, max_length=100)
    brand = serializers.PrimaryKeyRelatedField(
        queryset=Brand.objects.all(),
        required=False,
        allow_null=True,
    )
    attributes = serializers.PrimaryKeyRelatedField(
        queryset=ProductAttribute.objects.all(),
        many=True,
        required=False,
        help_text="Product attributes"
    )
    
    class Meta:
        model = Product
        fields = [
            'name',
            'category',
            'brand',
            'description',
            'short_description',
            'price',
            'original_price',
            'sku',
            'stock_quantity',
            'is_featured',
            'collection',
            'status',
            'image',
            'additional_images',
            'attributes',
        ]

    def validate_sku(self, value: str) -> str:
        # Extra hardening: prevent DB-level DataError for varchar(100)
        if value == "":
            return value
        if len(value) > 100:
            raise serializers.ValidationError("sku must be 100 characters or fewer.")
        return value

    def create(self, validated_data):
        additional_images = validated_data.pop('additional_images', [])
        attributes = validated_data.pop('attributes', [])
        sku = validated_data.get('sku')
        if sku == '':
            validated_data['sku'] = None
            sku = None

        if sku is not None and len(sku) > 100:
            raise serializers.ValidationError({"sku": "sku must be 100 characters or fewer."})

        product = Product.objects.create(**validated_data)

        # Set many-to-many relationships after creation
        if attributes:
            product.attributes.set(attributes)

        for index, image in enumerate(additional_images):
            ProductImage.objects.create(
                product=product,
                image=image,
                order=index + 1
            )

        return product

    def update(self, instance, validated_data):
        additional_images = validated_data.pop('additional_images', None)
        attributes = validated_data.pop('attributes', None)
        sku = validated_data.get('sku')
        if sku == '':
            validated_data['sku'] = instance.sku

        sku = validated_data.get('sku')
        if sku is not None and isinstance(sku, str) and len(sku) > 100:
            raise serializers.ValidationError({"sku": "sku must be 100 characters or fewer."})

        for attr, value in validated_data.items():
            if attr != 'attributes':
                setattr(instance, attr, value)

        instance.save()

        # Set many-to-many relationships after update
        if attributes is not None:
            instance.attributes.set(attributes)

        if additional_images:
            start_order = instance.images.count()
            for index, image in enumerate(additional_images):
                ProductImage.objects.create(
                    product=instance,
                    image=image,
                    order=start_order + index + 1
                )

        return instance


class HeroBannerListSerializer(serializers.ModelSerializer):
    """Serializer for public hero banner listing"""
    image = serializers.ImageField(use_url=True)

    # Hardening: DB is currently erroring with character varying(100) for hero-banners
    title = serializers.CharField(max_length=100, required=False)
    subtitle = serializers.CharField(max_length=100, required=False)
    cta_text = serializers.CharField(max_length=100, required=False)
    cta_url = serializers.CharField(max_length=100, required=False)

    class Meta:
        model = HeroBanner
        fields = [
            'id',
            'title',
            'subtitle',
            'cta_text',
            'cta_url',
            'image',
            'sort_order',
            'duration_seconds',
        ]
        read_only_fields = fields


class HeroBannerAdminSerializer(serializers.ModelSerializer):
    """Serializer for creating/updating hero banners"""
    image = serializers.ImageField(required=False, allow_null=True)

    # Hardening: DB is currently erroring with character varying(100) for hero-banners
    title = serializers.CharField(max_length=100, required=False, allow_blank=True)
    subtitle = serializers.CharField(max_length=100, required=False, allow_blank=True)
    cta_text = serializers.CharField(max_length=100, required=False, allow_blank=True)
    cta_url = serializers.CharField(max_length=100, required=False, allow_blank=True)

    class Meta:
        model = HeroBanner
        fields = [
            'id',
            'title',
            'subtitle',
            'cta_text',
            'cta_url',
            'image',
            'is_active',
            'sort_order',
'duration_seconds',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def validate(self, attrs):
        # Extra hardening so we never hit DB DataError: identify the exact field/length.
        length_checks = {
            "title": attrs.get("title"),
            "subtitle": attrs.get("subtitle"),
            "cta_text": attrs.get("cta_text"),
            "cta_url": attrs.get("cta_url"),
        }

        errors: dict[str, str] = {}
        for field_name, value in length_checks.items():
            if value is None:
                continue
            if isinstance(value, str) and len(value) > 100:
                errors[field_name] = "Must be 100 characters or fewer."

        if errors:
            raise serializers.ValidationError(errors)

        return attrs

    def update(self, instance, validated_data):
        # Allow partial update; ImageField is optional in payload
        return super().update(instance, validated_data)


class HomeAdBannerSerializer(serializers.ModelSerializer):
    """Public serializer for homepage ad banners."""
    image = serializers.ImageField(use_url=True)

    class Meta:
        model = HomeAdBanner
        fields = ['id', 'position', 'image', 'link_url', 'is_active', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class HomeAdBannerAdminSerializer(serializers.ModelSerializer):
    """Admin serializer for creating/updating homepage ad banners."""
    image = serializers.ImageField(required=False, allow_null=True)

    class Meta:
        model = HomeAdBanner
        fields = ['id', 'position', 'image', 'link_url', 'is_active', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']

    def update(self, instance, validated_data):
        return super().update(instance, validated_data)


class SiteSettingsSerializer(serializers.ModelSerializer):
    """Serializer for site settings"""
    
    class Meta:
        model = SiteSettings
        fields = [
            'id', 'site_name', 'site_description',
            'primary_color', 'secondary_color', 'accent_color',
            'contact_email', 'contact_phone', 'contact_address',
            'facebook_url', 'instagram_url', 'twitter_url', 'whatsapp_number',
            'free_shipping_threshold', 'shipping_flat_rate', 'local_shipping_rate',
            'tax_rate',
            'return_policy_days', 'return_policy_text',
            'site_logo', 'favicon',
            'is_maintenance_mode', 'maintenance_message',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def to_representation(self, instance):
        """Convert to representation with absolute URLs for images"""
        ret = super().to_representation(instance)
        if instance.site_logo:
            ret['site_logo'] = instance.site_logo.url
        if instance.favicon:
            ret['favicon'] = instance.favicon.url
        return ret


class SiteSettingsPublicSerializer(serializers.ModelSerializer):
    """Public serializer for site settings (non-sensitive data only)"""
    
    class Meta:
        model = SiteSettings
        fields = [
            'site_name', 'site_description',
            'site_logo',
            'primary_color', 'secondary_color', 'accent_color',
            'contact_email', 'contact_phone', 'contact_address',
            'facebook_url', 'instagram_url', 'twitter_url', 'whatsapp_number',
            'free_shipping_threshold', 'shipping_flat_rate', 'local_shipping_rate',
            'tax_rate',
            'return_policy_days', 'return_policy_text',
        ]
    
    def to_representation(self, instance):
        ret = super().to_representation(instance)

        if instance.site_logo:
            ret['site_logo'] = instance.site_logo.url
        else:
            ret['site_logo'] = None

        # Convert Decimal to string for JSON serialization
        if instance.free_shipping_threshold:
            ret['free_shipping_threshold'] = str(instance.free_shipping_threshold)
        if instance.shipping_flat_rate:
            ret['shipping_flat_rate'] = str(instance.shipping_flat_rate)
        if instance.local_shipping_rate:
            ret['local_shipping_rate'] = str(instance.local_shipping_rate)
        if instance.tax_rate is not None:
            ret['tax_rate'] = str(instance.tax_rate)
        return ret
