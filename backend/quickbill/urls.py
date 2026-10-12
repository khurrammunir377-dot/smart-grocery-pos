from django.urls import path
from . import views

urlpatterns = [
    path('', views.landing_page, name='quickbill_landing'),
    path('dashboard/', views.dashboard_view, name='quickbill_dashboard'),
    path('api/instant-create/', views.instant_invoice_create_api, name='instant_invoice_create'),
    path('view/<uuid:token>/', views.guest_invoice_view, name='guest_invoice_view'),
]
