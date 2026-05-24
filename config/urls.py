"""
URL configuration for Delchris Ecommerce Platform.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework.routers import DefaultRouter
from rest_framework.authtoken.views import obtain_auth_token

# API documentation
from rest_framework.schemas import get_schema_view

# Import all viewsets
from users.views import UserViewSet, UserAddressViewSet, UserWishlistViewSet, AdminSetupViewSet
from products.views import (
    CategoryViewSet,
    BrandViewSet,
    ProductViewSet,
    ProductAttributeViewSet,
    HeroBannerViewSet,
    HomeAdBannerViewSet,
    SiteSettingsViewSet,
)
from orders.views import OrderViewSet
from payments.views import PaymentViewSet, RefundViewSet, paystack_webhook
from reviews.views import ReviewViewSet

# Import analytics views
from analytics.views import (
    dashboard_metrics,
    dashboard_recent_orders,
    dashboard_sales_overview,
    dashboard_sales_daily,
    track_page_view,
    track_click,
    performance_summary,
    performance_breakdown,
)

# Create router and register viewsets
router = DefaultRouter()
router.register(r'users', UserViewSet, basename='user')
router.register(r'users/(?P<user_id>\d+)/addresses', UserAddressViewSet, basename='user-address')
router.register(r'users/(?P<user_id>\d+)/wishlist', UserWishlistViewSet, basename='user-wishlist')
router.register(r'categories', CategoryViewSet, basename='category')
router.register(r'brands', BrandViewSet, basename='brand')
router.register(r'hero-banners', HeroBannerViewSet, basename='hero-banner')
router.register(r'home-ads', HomeAdBannerViewSet, basename='home-ad')
router.register(r'attributes', ProductAttributeViewSet, basename='attribute')
router.register(r'products', ProductViewSet, basename='product')
router.register(r'orders', OrderViewSet, basename='order')
router.register(r'payments', PaymentViewSet, basename='payment')
router.register(r'refunds', RefundViewSet, basename='refund')
router.register(r'reviews', ReviewViewSet, basename='review')
router.register(r'admin/setup', AdminSetupViewSet, basename='admin-setup')
router.register(r'settings', SiteSettingsViewSet, basename='settings')

urlpatterns = [
    # Admin
    path('admin/', admin.site.urls),

    # API
    path('api/v1/', include(router.urls)),
    path('api/v1/auth/login/', obtain_auth_token, name='api_token_auth'),

    # Analytics (dashboard)
    path('api/v1/analytics/dashboard/metrics/', dashboard_metrics),
    path('api/v1/analytics/dashboard/sales-overview/', dashboard_sales_overview),
    path('api/v1/analytics/dashboard/sales-daily/', dashboard_sales_daily),
    path('api/v1/analytics/dashboard/recent-orders/', dashboard_recent_orders),

    # Analytics (performance / tracking)
    path('api/v1/analytics/track/page-view/', track_page_view),
    path('api/v1/analytics/track/click/', track_click),
    path('api/v1/analytics/dashboard/performance-summary/', performance_summary),
    path('api/v1/analytics/dashboard/performance-breakdown/', performance_breakdown),
    
    # API Documentation (using OpenAPI schema view)
    path('api/schema/', get_schema_view(title='Delchris API')),
    
    # Paystack Webhook
    path('api/v1/payments/webhook/', paystack_webhook, name='paystack-webhook'),
    
    # Payment explicit action routes (ensure they work properly with DRF)
    # These are explicit routes to the PaymentViewSet actions
    path('api/v1/payments/initialize/', PaymentViewSet.as_view({'post': 'initialize'}), name='payment-initialize'),
    path('api/v1/payments/verify/', PaymentViewSet.as_view({'post': 'verify'}), name='payment-verify'),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
