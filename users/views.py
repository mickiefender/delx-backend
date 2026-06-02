from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny, IsAdminUser
from django.contrib.auth import authenticate
from rest_framework.authtoken.models import Token

from .models import CustomUser, UserAddress, UserWishlist, DeviceToken, Notification
from .serializers import (
    UserSerializer, UserRegistrationSerializer, UserLoginSerializer,
    UserAddressSerializer, UserWishlistSerializer,
    AdminSetupSerializer,
    ForgotPasswordSerializer, ResetPasswordSerializer,
    DeviceTokenSerializer,
)
from .serializers_notifications import NotificationSerializer

from emailing.service import send_email
from emailing.templates import signup_email, login_email
from django.utils import timezone


class AdminSetupViewSet(viewsets.ViewSet):
    """ViewSet for admin setup - allows creating the first admin account"""
    permission_classes = [AllowAny]
    
    def list(self, request):
        """Check if admin exists"""
        admin_exists = CustomUser.objects.filter(is_staff=True, is_superuser=True).exists()
        return Response({
            'admin_exists': admin_exists,
            'message': 'Admin account exists' if admin_exists else 'No admin account found. Please create one.'
        })
    
    def create(self, request):
        """Create admin account if none exists"""
        admin_exists = CustomUser.objects.filter(is_staff=True, is_superuser=True).exists()
        
        if admin_exists:
            return Response(
                {'error': 'Admin account already exists. Please contact your administrator.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = AdminSetupSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            return Response({
                'message': 'Admin account created successfully',
                'user': UserSerializer(user).data
            }, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UserViewSet(viewsets.ModelViewSet):
    """ViewSet for user management"""
    queryset = CustomUser.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]
    
    def get_serializer_class(self):
        if self.action == 'create':
            return UserRegistrationSerializer
        elif self.action == 'login':
            return UserLoginSerializer
        return UserSerializer
    
    def get_permissions(self):
        if self.action in ['create', 'login', 'register', 'admin_login']:
            return [AllowAny()]
        return [IsAuthenticated()]
    
    @action(detail=False, methods=['post'], permission_classes=[AllowAny()])
    def register(self, request):
        """User registration endpoint"""
        serializer = UserRegistrationSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            token, created = Token.objects.get_or_create(user=user)

            # Email customer (async, best-effort)
            if user.email:
                try:
                    from emailing.tasks import send_signup_email_task

                    send_signup_email_task.delay(
                        user_id=user.id,
                        user_email=user.email,
                        username=user.username,
                    )
                except Exception:
                    pass

            return Response({
                'user': UserSerializer(user).data,
                'token': token.key
            }, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['post'], permission_classes=[AllowAny()])
    def login(self, request):
        """User login endpoint"""
        email = request.data.get('email')
        password = request.data.get('password')
        
        # Use filter().first() to handle duplicate emails gracefully
        user = CustomUser.objects.filter(email__iexact=email).first()
        
        if not user:
            return Response(
                {'error': 'Invalid credentials'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        # Check password
        if not user.check_password(password):
            return Response(
                {'error': 'Invalid credentials'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        if not user.is_active:
            return Response(
                {'error': 'User account is disabled'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        token, created = Token.objects.get_or_create(user=user)

        # Email customer (async, best-effort)
        if user.email:
            try:
                from emailing.tasks import send_login_email_task

                send_login_email_task.delay(
                    user_id=user.id,
                    user_email=user.email,
                    username=user.username,
                )
            except Exception:
                pass

        return Response({
            'user': UserSerializer(user).data,
            'token': token.key
        }, status=status.HTTP_200_OK)
    
    @action(detail=False, methods=['post'], permission_classes=[AllowAny()])
    def admin_login(self, request):
        """Admin login endpoint - requires is_staff or is_superuser"""
        email = request.data.get('email')
        password = request.data.get('password')
        
        # Use filter().first() to handle duplicate emails gracefully
        user = CustomUser.objects.filter(email__iexact=email).first()
        
        if not user:
            return Response(
                {'error': 'Invalid credentials'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        # Check password
        if not user.check_password(password):
            return Response(
                {'error': 'Invalid credentials'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        if not user.is_active:
            return Response(
                {'error': 'User account is disabled'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Check if user is admin (staff or superuser)
        if not user.is_staff and not user.is_superuser:
            return Response(
                {'error': 'Access denied. Admin credentials required.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        token, created = Token.objects.get_or_create(user=user)
        return Response({
            'user': UserSerializer(user).data,
'token': token.key
        }, status=status.HTTP_200_OK)
    
    @action(detail=False, methods=['get', 'put'])
    def me(self, request):
        """Get or update current user profile"""
        if request.method == 'GET':
            serializer = self.get_serializer(request.user)
            return Response(serializer.data)
        elif request.method == 'PUT':
            serializer = self.get_serializer(request.user, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['post'])
    def logout(self, request):
        """Logout user"""
        request.user.auth_token.delete()
        return Response({'message': 'Logged out successfully'}, status=status.HTTP_200_OK)
    
    @action(detail=False, methods=['post'], permission_classes=[AllowAny()])
    def forgot_password(self, request):
        """Request password reset - sends email with reset link"""
        from django.conf import settings
        
        serializer = ForgotPasswordSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        email = serializer.validated_data['email']
        
        # Find user by email (case-insensitive)
        user = CustomUser.objects.filter(email__iexact=email).first()
        
        # Always return success to prevent email enumeration
        # But only send email if user exists
        if user and user.is_active:
            # Create password reset token
            from .models import PasswordResetToken
            reset_token = PasswordResetToken.create_token(user)
            
            # Build reset URL
            frontend_base = getattr(settings, 'FRONTEND_URL', 'http://localhost:3000')
            reset_url = f"{frontend_base}/auth/reset-password?token={reset_token.token}"
            
            # Send password reset email (async, best-effort)
            if user.email:
                try:
                    from emailing.tasks import send_password_reset_email_task
                    
                    send_password_reset_email_task.delay(
                        user_email=user.email,
                        username=user.username,
                        reset_url=reset_url,
                    )
                except Exception:
                    pass
        
        return Response({
            'message': 'If an account exists with that email, a password reset link has been sent.'
        }, status=status.HTTP_200_OK)
    
    @action(detail=False, methods=['post'], permission_classes=[AllowAny()])
    def reset_password(self, request):
        """Reset password using token"""
        serializer = ResetPasswordSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        user = serializer.save()
        
        # Send confirmation email (async, best-effort)
        if user.email:
            try:
                from emailing.tasks import send_password_reset_confirmation_email_task
                
                send_password_reset_confirmation_email_task.delay(
                    user_email=user.email,
                    username=user.username,
                )
            except Exception:
                pass
        
        return Response({
            'message': 'Password has been reset successfully. Please login with your new password.'
        }, status=status.HTTP_200_OK)

    @action(
        detail=False,
        methods=['post'],
        permission_classes=[IsAuthenticated],
        url_path='device-token',
    )
    def register_device_token(self, request):
        """
        Register or update an FCM device token for the authenticated user.

        Body:
          { "platform": "android" | "ios", "token": "<fcm_token>" }
        """
        serializer = DeviceTokenSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        platform = serializer.validated_data['platform']
        token = serializer.validated_data['token']

        try:
            device_token = DeviceToken.objects.filter(token=token).first()
            if device_token:
                device_token.user = request.user
                device_token.platform = platform
                device_token.last_seen_at = timezone.now()
                device_token.save(update_fields=['user', 'platform', 'last_seen_at'])
            else:
                device_token = DeviceToken.objects.create(
                    user=request.user,
                    platform=platform,
                    token=token,
                    last_seen_at=timezone.now(),
                )

            return Response(
                {
                    'message': 'Device token registered',
                    'platform': device_token.platform,
                    'token': device_token.token,
                },
                status=status.HTTP_201_CREATED,
            )
        except Exception as e:
            return Response(
                {'error': f'Failed to register device token: {str(e)}'},
                status=status.HTTP_400_BAD_REQUEST,
            )


class UserAddressViewSet(viewsets.ModelViewSet):
    """ViewSet for user addresses"""
    serializer_class = UserAddressSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        user_id = self.kwargs.get('user_id')
        return UserAddress.objects.filter(user_id=user_id)
    
    def perform_create(self, serializer):
        user_id = self.kwargs.get('user_id')
        serializer.save(user_id=user_id)


class UserWishlistViewSet(viewsets.ModelViewSet):
    """ViewSet for user wishlists"""
    serializer_class = UserWishlistSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        user_id = self.kwargs.get('user_id')
        return UserWishlist.objects.filter(user_id=user_id)
    
    @action(detail=False, methods=['post'])
    def add_product(self, request):
        """Add product to wishlist"""
        user_id = self.kwargs.get('user_id')
        product_id = request.data.get('product_id')
        
        try:
            wishlist = UserWishlist.objects.get(user_id=user_id)
            wishlist.products.add(product_id)
            return Response({'message': 'Product added to wishlist'})
        except UserWishlist.DoesNotExist:
            return Response({'error': 'Wishlist not found'}, status=status.HTTP_404_NOT_FOUND)
    
    @action(detail=False, methods=['post'])
    def remove_product(self, request):
        """Remove product from wishlist"""
        user_id = self.kwargs.get('user_id')
        product_id = request.data.get('product_id')
        
        try:
            wishlist = UserWishlist.objects.get(user_id=user_id)
            wishlist.products.remove(product_id)
            return Response({'message': 'Product removed from wishlist'})
        except UserWishlist.DoesNotExist:
            return Response({'error': 'Wishlist not found'}, status=status.HTTP_404_NOT_FOUND)


class NotificationViewSet(viewsets.ModelViewSet):
    """
    ViewSet for user notifications.
    Provides CRUD operations for notifications.
    """
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Return notifications for the authenticated user"""
        return Notification.objects.filter(user=self.request.user)

    def list(self, request, *args, **kwargs):
        """List all notifications for the user"""
        queryset = self.get_queryset()

        # Optionally filter by read status
        is_read = request.query_params.get('is_read')
        if is_read is not None:
            queryset = queryset.filter(is_read=is_read.lower() == 'true')

        # Optionally filter by type
        notification_type = request.query_params.get('type')
        if notification_type:
            queryset = queryset.filter(type=notification_type)

        serializer = self.get_serializer(queryset, many=True)
        return Response({'results': serializer.data})

    def partial_update(self, request, *args, **kwargs):
        """Update a single notification (mark as read)"""
        kwargs['partial'] = True
        return self.update(request, *args, **kwargs)

    @action(detail=False, methods=['patch'])
    def mark_all_read(self, request):
        """Mark all notifications as read"""
        notifications = self.get_queryset()
        notifications.update(is_read=True)
        return Response({'message': 'All notifications marked as read'})
