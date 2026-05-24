from rest_framework import serializers
from django.contrib.auth import authenticate
from django.db import IntegrityError
from .models import CustomUser, UserAddress, UserWishlist


class UserSerializer(serializers.ModelSerializer):
    """Serializer for user profile"""
    
    full_name = serializers.SerializerMethodField()
    
    class Meta:
        model = CustomUser
        fields = [
            'id', 'username', 'email', 'full_name', 'phone_number',
            'profile_image', 'bio', 'gender', 'date_of_birth',
            'is_verified', 'is_staff', 'is_superuser',
            'preferred_currency', 'preferred_language',
            'newsletter_subscribed', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'is_verified']
    
    def get_full_name(self, obj):
        return obj.get_full_name()


class UserRegistrationSerializer(serializers.ModelSerializer):
    """Serializer for user registration"""
    
    password = serializers.CharField(write_only=True, min_length=8)
    password2 = serializers.CharField(write_only=True, min_length=8)
    
    class Meta:
        model = CustomUser
        fields = ['email', 'username', 'first_name', 'last_name', 'phone_number', 'password', 'password2']
    
    def validate(self, data):
        password2 = data.pop('password2', None)
        if password2 is None or data.get('password') != password2:
            raise serializers.ValidationError({'password': 'Passwords must match'})
        
        # Give clear, consistent errors for duplicates
        username = data.get('username')
        email = data.get('email')
        if username and CustomUser.objects.filter(username=username).exists():
            raise serializers.ValidationError({'username': 'A user with that username already exists.'})
        if email and CustomUser.objects.filter(email__iexact=email).exists():
            raise serializers.ValidationError({'email': 'A user with that email already exists.'})
        
        return data
    
    def create(self, validated_data):
        try:
            user = CustomUser.objects.create_user(**validated_data)
            return user
        except IntegrityError:
            username = validated_data.get('username')
            email = validated_data.get('email')

            errors: dict[str, str] = {}

            if username and CustomUser.objects.filter(username=username).exists():
                errors['username'] = 'A user with that username already exists.'
            if email and CustomUser.objects.filter(email__iexact=email).exists():
                errors['email'] = 'A user with that email already exists.'

            if not errors:
                errors['non_field_errors'] = 'Registration failed due to a constraint violation.'

            raise serializers.ValidationError(errors)


class UserLoginSerializer(serializers.Serializer):
    """Serializer for user login"""
    
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
    
    def validate(self, data):
        # Authenticate using email instead of username
        email = data.get('email', '').lower()
        password = data.get('password', '')
        
        try:
            user = CustomUser.objects.get(email__iexact=email)
        except CustomUser.DoesNotExist:
            raise serializers.ValidationError('Invalid credentials')
        
        # Check password
        if not user.check_password(password):
            raise serializers.ValidationError('Invalid credentials')
        
        if not user.is_active:
            raise serializers.ValidationError('User account is disabled')
        
        data['user'] = user
        return data


class AdminSetupSerializer(serializers.ModelSerializer):
    """Serializer for initial admin setup"""
    
    password = serializers.CharField(write_only=True, min_length=8)
    password2 = serializers.CharField(write_only=True, min_length=8)
    
    class Meta:
        model = CustomUser
        fields = ['username', 'email', 'password', 'password2']
    
    def validate(self, data):
        if data['password'] != data['password2']:
            raise serializers.ValidationError({'password': 'Passwords must match'})
        
        # Check if username already exists
        if CustomUser.objects.filter(username=data['username']).exists():
            raise serializers.ValidationError({'username': 'Username already exists'})
        
        # Check if email already exists
        if CustomUser.objects.filter(email=data['email']).exists():
            raise serializers.ValidationError({'email': 'Email already exists'})
        
        return data
    
    def create(self, validated_data):
        # Remove password2 before creating user
        validated_data.pop('password2')
        
        user = CustomUser.objects.create_user(
            **validated_data,
            is_staff=True,
            is_superuser=True,
            is_active=True
        )
        return user


class UserAddressSerializer(serializers.ModelSerializer):
    """Serializer for user addresses"""
    
    class Meta:
        model = UserAddress
        fields = [
            'id', 'address_type', 'first_name', 'last_name', 'phone_number',
            'email', 'street_address', 'city', 'state_province', 'postal_code',
            'country', 'is_default', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class UserWishlistSerializer(serializers.ModelSerializer):
    """Serializer for user wishlist"""
    
    products = serializers.SerializerMethodField()
    
    class Meta:
        model = UserWishlist
        fields = ['id', 'products', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']
    
def get_products(self, obj):
        from products.serializers import ProductListSerializer
        return ProductListSerializer(obj.products.all(), many=True).data


class ForgotPasswordSerializer(serializers.Serializer):
    """Serializer for forgot password request"""
    
    email = serializers.EmailField()
    
    def validate_email(self, value):
        # Always normalize to lowercase for lookup
        return value.lower()


class ResetPasswordSerializer(serializers.Serializer):
    """Serializer for password reset"""
    
    token = serializers.CharField(min_length=64, max_length=128)
    password = serializers.CharField(write_only=True, min_length=8)
    password2 = serializers.CharField(write_only=True, min_length=8)
    
    def validate(self, data):
        password = data.get('password')
        password2 = data.get('password2')
        
        if password != password2:
            raise serializers.ValidationError({'password': 'Passwords must match'})
        
        # Validate token exists and is valid
        from .models import PasswordResetToken
        token = data.get('token')
        
        try:
            reset_token = PasswordResetToken.objects.get(token=token)
        except PasswordResetToken.DoesNotExist:
            raise serializers.ValidationError({'token': 'Invalid or expired token'})
        
        if not reset_token.is_valid():
            raise serializers.ValidationError({'token': 'Invalid or expired token'})
        
        data['reset_token'] = reset_token
        return data
    
    def save(self):
        """Reset the user's password"""
        reset_token = self.validated_data['reset_token']
        new_password = self.validated_data['password']
        
        user = reset_token.user
        user.set_password(new_password)
        user.save()
        
        # Mark token as used
        reset_token.used = True
        reset_token.save()
        
        # Optionally invalidate all other tokens for this user
        PasswordResetToken.objects.filter(user=user, used=False).update(used=True)
        
        return user
