from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from quickbill.views import landing_page
from billing.views import laptop_pos_view

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', laptop_pos_view, name='pos_counter'),
    path('pos/', laptop_pos_view, name='pos_counter_alias'),
    path('landing/', landing_page, name='saas_landing'),
    path('home/', landing_page, name='saas_home'),
    path('quickbill/', include('quickbill.urls')),
    path('', include('billing.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
