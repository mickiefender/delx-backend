from django.contrib import admin

from .models import (
    Category,
    Brand,
    Product,
    ProductImage,
    ProductVariant,
    ProductAttribute,
    HeroBanner,
    HomeAdBanner,
)


@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'slug', 'is_active', 'created_at', 'updated_at')
    list_filter = ('is_active',)
    search_fields = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ('created_at', 'updated_at')


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'slug', 'is_active', 'is_featured', 'created_at', 'updated_at')
    list_filter = ('is_active', 'is_featured')
    search_fields = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ('created_at', 'updated_at')


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'name',
        'slug',
        'category',
        'brand',
        'price',
        'stock_quantity',
        'collection',
        'is_featured',
        'status',
        'created_at',
        'updated_at',
    )
    list_filter = ('status', 'collection', 'is_featured', 'category', 'brand')
    search_fields = ('name', 'slug', 'sku')
    autocomplete_fields = ('category', 'brand', 'created_by')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(ProductImage)
class ProductImageAdmin(admin.ModelAdmin):
    list_display = ('id', 'product', 'order', 'is_primary', 'created_at')
    list_filter = ('is_primary',)
    search_fields = ('product__name',)
    autocomplete_fields = ('product',)


@admin.register(ProductVariant)
class ProductVariantAdmin(admin.ModelAdmin):
    list_display = ('id', 'product', 'name', 'sku', 'price', 'stock_quantity', 'created_at')
    search_fields = ('product__name', 'sku', 'name')
    autocomplete_fields = ('product',)


@admin.register(ProductAttribute)
class ProductAttributeAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'slug', 'is_active', 'created_at', 'updated_at')
    list_filter = ('is_active',)
    search_fields = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ('created_at', 'updated_at')


@admin.register(HeroBanner)
class HeroBannerAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'cta_url', 'is_active', 'sort_order', 'duration_seconds', 'created_at', 'updated_at')
    list_filter = ('is_active',)
    search_fields = ('title', 'cta_url')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(HomeAdBanner)
class HomeAdBannerAdmin(admin.ModelAdmin):
    list_display = ('id', 'position', 'link_url', 'is_active', 'created_at', 'updated_at')
    list_filter = ('is_active', 'position')
    search_fields = ('link_url',)
    readonly_fields = ('created_at', 'updated_at')
