from django.contrib import admin
from .models import BusinessProfile, Invoice, InvoiceItem, VisitorLog, RegisteredMerchant

@admin.register(VisitorLog)
class VisitorLogAdmin(admin.ModelAdmin):
    list_display = ('ip_address', 'path', 'device_type', 'user', 'visited_at')
    list_filter = ('device_type', 'visited_at', 'path')
    search_fields = ('ip_address', 'user_agent', 'path')
    readonly_fields = ('visited_at',)

@admin.register(RegisteredMerchant)
class RegisteredMerchantAdmin(admin.ModelAdmin):
    list_display = ('store_name', 'phone', 'business_type', 'city', 'country', 'is_active', 'created_at')
    list_filter = ('business_type', 'country', 'is_active', 'created_at')
    search_fields = ('store_name', 'phone', 'user__username', 'user__email')

admin.site.register(BusinessProfile)
admin.site.register(Invoice)
admin.site.register(InvoiceItem)
