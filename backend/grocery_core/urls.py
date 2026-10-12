from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from quickbill.views import landing_page, dashboard_view
from billing.views import laptop_pos_view

urlpatterns = [
    path('django-admin/', admin.site.urls),
    path('', landing_page, name='landing_home'),
    path('pos/', laptop_pos_view, name='pos_counter'),
    path('admin-panel/', dashboard_view, name='admin_panel'),
    path('quickbill/', include('quickbill.urls')),
    path('', include('billing.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
