from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, UserAddress, UserWishlist


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ('Additional Info', {'fields': ('phone_number', 'bio', 'gender', 'date_of_birth', 'is_verified', 'preferred_currency', 'preferred_language', 'newsletter_subscribed')}),
    )
    list_display = ('username', 'email', 'is_verified', 'newsletter_subscribed', 'created_at')
    list_filter = UserAdmin.list_filter + ('is_verified', 'newsletter_subscribed')


@admin.register(UserAddress)
class UserAddressAdmin(admin.ModelAdmin):
    list_display = ('get_user', 'address_type', 'city', 'country', 'is_default', 'created_at')
    list_filter = ('address_type', 'is_default', 'country')
    search_fields = ('user__username', 'street_address', 'city')
    
    def get_user(self, obj):
        return obj.user.username
    get_user.short_description = 'User'


@admin.register(UserWishlist)
class UserWishlistAdmin(admin.ModelAdmin):
    list_display = ('user', 'product_count', 'created_at')
    search_fields = ('user__username',)
    
    def product_count(self, obj):
        return obj.products.count()
    product_count.short_description = 'Products'
