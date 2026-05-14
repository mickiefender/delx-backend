from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAdminUser
from django_filters.rest_framework import DjangoFilterBackend

from .models import Category, Brand, Product, HeroBanner, HomeAdBanner, ProductAttribute, SiteSettings
from .serializers import (
    CategorySerializer,
    BrandSerializer,
    ProductListSerializer,
    ProductDetailSerializer,
    ProductCreateUpdateSerializer,
    ProductAttributeSerializer,
    HeroBannerListSerializer,
    HeroBannerAdminSerializer,
    HomeAdBannerSerializer,
    HomeAdBannerAdminSerializer,
    SiteSettingsSerializer,
    SiteSettingsPublicSerializer,
)


class BrandViewSet(viewsets.ModelViewSet):
    """Public viewset for product brands"""
    queryset = Brand.objects.all()
    serializer_class = BrandSerializer
    lookup_field = 'slug'

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAdminUser()]
        return [AllowAny()]

    def get_queryset(self):
        if self.request.user and self.request.user.is_staff:
            return Brand.objects.all()
        return Brand.objects.filter(is_active=True)


class CategoryViewSet(viewsets.ModelViewSet):
    """ViewSet for product categories"""
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    lookup_field = 'slug'

    def get_queryset(self):
        # Public endpoints only show active categories, but admin delete/update must
        # be able to fetch inactive categories too (otherwise DRF returns 404).
        if self.action in ['list', 'featured', 'products', 'retrieve']:
            return Category.objects.filter(is_active=True)
        return Category.objects.all()

    def get_object(self):
        """
        Allow lookup by both numeric id and slug.
        Frontend currently calls /categories/{id}/ for DELETE/PATCH.
        """
        queryset = self.get_queryset()
        lookup_url_kwarg = self.lookup_url_kwarg or self.lookup_field
        lookup_value = self.kwargs.get(lookup_url_kwarg)

        if not lookup_value:
            return super().get_object()

        # Try numeric PK first
        try:
            return queryset.get(pk=int(lookup_value))
        except (ValueError, Category.DoesNotExist):
            pass

        # Fallback to slug
        return queryset.get(slug=lookup_value)

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAdminUser()]
        return [AllowAny()]

    @action(detail=False, methods=['get'])
    def featured(self, request):
        """Get featured categories (for homepage)"""
        categories = Category.objects.filter(is_active=True, is_featured=True).order_by('name')
        serializer = CategorySerializer(categories, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def products(self, request, slug=None):
        """Get products in a category"""
        category = self.get_object()
        products = category.products.filter(status='active')
        serializer = ProductListSerializer(products, many=True)
        return Response(serializer.data)


class HeroBannerViewSet(viewsets.ModelViewSet):
    """ViewSet for hero banners"""
    queryset = HeroBanner.objects.all()
    serializer_class = HeroBannerListSerializer
    lookup_field = 'id'


class HomeAdBannerViewSet(viewsets.ModelViewSet):
    """ViewSet for homepage ad banners (2 images). Public read, admin write."""
    queryset = HomeAdBanner.objects.all()
    serializer_class = HomeAdBannerSerializer
    lookup_field = 'position'

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAdminUser()]
        return [AllowAny()]

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return HomeAdBannerAdminSerializer
        return HomeAdBannerSerializer

    def create(self, request, *args, **kwargs):
        from django.db.utils import DataError
        try:
            return super().create(request, *args, **kwargs)
        except DataError as exc:
            return Response(
                {"detail": f"Invalid input (db constraint): {str(exc)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

    def update(self, request, *args, **kwargs):
        from django.db.utils import DataError
        try:
            return super().update(request, *args, **kwargs)
        except DataError as exc:
            return Response(
                {"detail": f"Invalid input (db constraint): {str(exc)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )


class ProductAttributeViewSet(viewsets.ModelViewSet):
    """ViewSet for product attributes"""
    queryset = ProductAttribute.objects.all()
    serializer_class = ProductAttributeSerializer
    lookup_field = 'slug'

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAdminUser()]
        return [AllowAny()]

    def get_queryset(self):
        if self.request.user and self.request.user.is_staff:
            return ProductAttribute.objects.all()
        return ProductAttribute.objects.filter(is_active=True)

    @action(detail=True, methods=['get'])
    def products(self, request, slug=None):
        """Get products with this attribute"""
        attribute = self.get_object()
        products = attribute.products.filter(status='active')
        from .serializers import ProductListSerializer
        serializer = ProductListSerializer(products, many=True)
        return Response(serializer.data)


class ProductViewSet(viewsets.ModelViewSet):
    """ViewSet for products"""
    queryset = Product.objects.all()
    lookup_field = 'id'
    lookup_value_converters = {
        'id': 'int',
        'slug': 'slug',
    }
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['category', 'brand', 'price', 'status']
    search_fields = ['name', 'description', 'sku']
    ordering_fields = ['price', 'rating', 'created_at', 'review_count']
    ordering = ['-created_at']

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAdminUser()]
        return [AllowAny()]

    def get_queryset(self):
        queryset = Product.objects.all()
        if self.request.user and self.request.user.is_staff:
            return queryset
        return queryset.filter(status='active')

    def get_object(self):
        """Allow lookup by both id and slug"""
        queryset = self.get_queryset()
        lookup_url_kwarg = self.lookup_url_kwarg or self.lookup_field

        lookup_value = self.kwargs.get(lookup_url_kwarg)

        if not lookup_value:
            return super().get_object()

        try:
            return queryset.get(pk=lookup_value)
        except Product.DoesNotExist:
            pass
        except ValueError:
            pass

        try:
            return queryset.get(slug=lookup_value)
        except Product.DoesNotExist:
            pass

        from django.http import Http404
        raise Http404(f"Product with identifier '{lookup_value}' not found.")

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return ProductDetailSerializer
        elif self.action in ['create', 'update', 'partial_update']:
            return ProductCreateUpdateSerializer
        return ProductListSerializer

    @action(detail=True, methods=['get'])
    def reviews(self, request, slug=None):
        """Get reviews for a product"""
        product = self.get_object()
        reviews = product.reviews.filter(is_approved=True)
        """Get featured products"""
        products = self.get_queryset().filter(is_featured=True)[:8]
        serializer = ProductListSerializer(products, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def best_sellers(self, request):
        """Get best selling products"""
        products = self.get_queryset().order_by('-review_count')[:10]
        serializer = ProductListSerializer(products, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def by_collection(self, request):
        """Get products by collection type (new_arrival, best_seller, special_offer)"""
        collection = request.query_params.get('collection', 'none')
        valid_collections = ['new_arrival', 'best_seller', 'special_offer']
        
        if collection not in valid_collections:
            return Response(
                {"detail": f"Invalid collection. Must be one of: {', '.join(valid_collections)}"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        products = self.get_queryset().filter(collection=collection)[:12]
        serializer = ProductListSerializer(products, many=True)
        return Response(serializer.data)


class SiteSettingsViewSet(viewsets.ModelViewSet):
    """ViewSet for site settings (singleton - only one instance)"""
    queryset = SiteSettings.objects.all()
    lookup_field = 'id'
    
    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAdminUser()]
        return [AllowAny()]
    
    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return SiteSettingsSerializer
        return SiteSettingsSerializer
    
    def get_object(self):
        """Override to always return the single settings instance"""
        queryset = self.get_queryset()
        try:
            return queryset.first()
        except SiteSettings.DoesNotExist:
            return None
    
    def list(self, request, *args, **kwargs):
        """Get the settings (or create default if none exists)"""
        settings = SiteSettings.objects.first()
        if not settings:
            # Create default settings if none exists
            settings = SiteSettings.objects.create()
        serializer = self.get_serializer(settings)
        return Response(serializer.data)
    
    def retrieve(self, request, *args, **kwargs):
        """Get single settings instance"""
        settings = SiteSettings.objects.first()
        if not settings:
            settings = SiteSettings.objects.create()
        serializer = self.get_serializer(settings)
        return Response(serializer.data)
    
    def create(self, request, *args, **kwargs):
        """Prevent duplicate creation - always use update"""
        settings = SiteSettings.objects.first()
        if settings:
            return self.update(request, *args, **kwargs)
        return super().create(request, *args, **kwargs)
    
    @action(detail=False, methods=['get'])
    def public(self, request):
        """Public endpoint for non-sensitive settings"""
        settings = SiteSettings.objects.first()
        if not settings:
            settings = SiteSettings.objects.create()
        serializer = SiteSettingsPublicSerializer(settings)
        return Response(serializer.data)
