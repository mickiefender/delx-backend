from rest_framework import serializers
from products.models import Product
from .models import Review, ReviewImage, ReviewResponse


class ReviewImageSerializer(serializers.ModelSerializer):
    """Serializer for review images"""
    
    class Meta:
        model = ReviewImage
        fields = ['id', 'image']
        read_only_fields = ['id']


class ReviewResponseSerializer(serializers.ModelSerializer):
    """Serializer for review responses"""
    
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    
    class Meta:
        model = ReviewResponse
        fields = ['id', 'content', 'user', 'user_name', 'created_at']
        read_only_fields = ['id', 'user_name', 'created_at']


class ReviewListSerializer(serializers.ModelSerializer):
    """Serializer for review list"""
    
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    images = ReviewImageSerializer(many=True, read_only=True)
    
    class Meta:
        model = Review
        fields = [
            'id', 'product', 'user_name', 'title', 'content', 'rating',
            'is_verified_purchase', 'helpful_count', 'images', 'created_at'
        ]
        read_only_fields = fields


class ReviewDetailSerializer(serializers.ModelSerializer):
    """Serializer for review detail"""
    
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    user_image = serializers.CharField(source='user.profile_image', read_only=True)
    images = ReviewImageSerializer(many=True, read_only=True)
    response = ReviewResponseSerializer(read_only=True)
    
    class Meta:
        model = Review
        fields = [
            'id', 'product', 'user', 'user_name', 'user_image', 'title', 'content',
            'rating', 'is_verified_purchase', 'helpful_count', 'unhelpful_count',
            'images', 'response', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'user_name', 'user_image', 'helpful_count', 'unhelpful_count',
            'is_verified_purchase', 'created_at', 'updated_at'
        ]


class ReviewCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating reviews"""
    
    product = serializers.PrimaryKeyRelatedField(queryset=Product.objects.all())
    
    class Meta:
        model = Review
        fields = ['product', 'title', 'content', 'rating']
    
    def create(self, validated_data):
        review = Review.objects.create(**validated_data)
        return review
