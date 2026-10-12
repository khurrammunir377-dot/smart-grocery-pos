from django.urls import path
from . import views

urlpatterns = [
    path('', views.landing_page, name='quickbill_landing'),
    path('dashboard/', views.dashboard_view, name='quickbill_dashboard'),
    path('admin-panel/', views.dashboard_view, name='quickbill_admin_panel'),
    path('api/register-merchant/', views.register_merchant_api, name='register_merchant_api'),
    path('api/login-merchant/', views.login_merchant_api, name='login_merchant_api'),
    path('logout/', views.logout_merchant_view, name='logout_merchant'),
    path('api/instant-create/', views.instant_invoice_create_api, name='instant_invoice_create'),
    path('view/<uuid:token>/', views.guest_invoice_view, name='guest_invoice_view'),
]
