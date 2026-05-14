from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny, IsAdminUser
from django.contrib.auth import authenticate
from rest_framework.authtoken.models import Token

from .models import CustomUser, UserAddress, UserWishlist
from .serializers import (
    UserSerializer, UserRegistrationSerializer, UserLoginSerializer,
    UserAddressSerializer, UserWishlistSerializer,
    AdminSetupSerializer,
)

from emailing.service import send_email
from emailing.templates import signup_email, login_email


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
