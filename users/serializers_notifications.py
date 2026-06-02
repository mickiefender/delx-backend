"""
Serializers for the Notification model.
"""
from rest_framework import serializers
from .models import Notification


class NotificationSerializer(serializers.ModelSerializer):
    """
    Serializer for Notification model.
    """
    class Meta:
        model = Notification
        fields = [
            'id',
            'title',
            'message',
            'type',
            'is_read',
            'order_id',
            'product_id',
            'data',
            'created_at',
        ]
        read_only_fields = ['id', 'user', 'created_at']


class NotificationCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating notifications.
    """
    class Meta:
        model = Notification
        fields = [
            'title',
            'message',
            'type',
            'order_id',
            'product_id',
            'data',
        ]
    
    def create(self, validated_data):
        # Set user from context
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)


class NotificationListSerializer(serializers.ModelSerializer):
    """
    Simplified serializer for notification list views.
    """
    class Meta:
        model = Notification
        fields = [
            'id',
            'title',
            'message',
            'type',
            'is_read',
            'order_id',
            'product_id',
            'created_at',
        ]
        read_only_fields = fields
