from django.urls import path
from . import views

urlpatterns = [
    path('pos-counter/', views.laptop_pos_view, name='pos_home'),
    
    # 1. Sales & Billing
    path('api/parse-preview/', views.parse_preview_api, name='parse_preview'),
    path('api/create-invoice/', views.create_invoice_api, name='create_invoice'),
    path('api/refund-invoice/', views.refund_invoice_api, name='refund_invoice'),
    path('api/invoice-detail/<str:token>/', views.invoice_detail_api, name='invoice_detail'),
    path('bill/view/<str:token>/', views.public_bill_view, name='public_bill'),

    # 2. Inventory & Stock
    path('api/inventory-list/', views.inventory_list_api, name='inventory_list'),
    path('api/stock-adjust/', views.stock_adjust_api, name='stock_adjust'),
    path('api/quick-stock-in/', views.quick_stock_in_api, name='quick_stock_in'),
    path('api/update-product/', views.update_product_api, name='update_product'),
    path('api/delete-product/', views.delete_product_api, name='delete_product'),
    path('api/barcode-lookup/', views.barcode_lookup_api, name='barcode_lookup'),

    # 3. Purchases & Suppliers
    path('api/suppliers-list/', views.suppliers_list_api, name='suppliers_list'),
    path('api/add-supplier/', views.add_supplier_api, name='add_supplier'),
    path('api/create-purchase/', views.create_purchase_bill_api, name='create_purchase'),
    path('api/pay-supplier/', views.pay_supplier_api, name='pay_supplier'),

    # 4. Customers & Khata
    path('api/khata-list/', views.khata_list_api, name='khata_list'),
    path('api/add-customer/', views.add_customer_api, name='add_customer'),
    path('api/khata-pay/', views.khata_pay_api, name='khata_pay'),
    path('api/customer-statement/', views.customer_statement_api, name='customer_statement'),

    # 5. Accounts & Expenses
    path('api/expenses-list/', views.expenses_list_api, name='expenses_list'),
    path('api/add-expense/', views.add_expense_api, name='add_expense'),
    path('api/cash-drawer-status/', views.cash_drawer_status_api, name='cash_drawer_status'),
    path('api/open-cash-drawer/', views.open_cash_drawer_api, name='open_cash_drawer'),
    path('api/close-cash-drawer/', views.close_cash_drawer_api, name='close_cash_drawer'),

    # 6. Reports & Analytics
    path('api/reports-summary/', views.reports_summary_api, name='reports_summary'),
    path('api/advanced-reports/', views.advanced_reports_api, name='advanced_reports'),

    # 7. Users & Permissions
    path('api/verify-pin/', views.verify_pin_api, name='verify_pin'),
    path('api/staff-list/', views.staff_list_api, name='staff_list'),
    path('api/create-staff-user/', views.create_staff_user_api, name='create_staff_user'),

    # 8. Excel Import
    path('api/upload-inventory-excel/', views.upload_inventory_excel_api, name='upload_inventory_excel'),
    path('api/send-whatsapp-silent/', views.send_whatsapp_silent_api, name='send_whatsapp_silent'),
]
