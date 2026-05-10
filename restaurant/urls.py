from django.urls import path

from . import views

app_name = 'restaurant'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('owner/', views.owner_dashboard, name='owner_dashboard'),
    path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('suppliers/', views.suppliers_dashboard, name='suppliers_dashboard'),
    path('purchases/', views.purchase_dashboard, name='purchase_dashboard'),
    path('purchases/search-items/', views.purchase_item_search, name='purchase_item_search'),
    path('inventory/', views.inventory_dashboard, name='inventory_dashboard'),
    path('inventory/<int:item_id>/history/', views.inventory_item_history, name='inventory_item_history'),
    path('pos/', views.pos_dashboard, name='pos_dashboard'),
    path('waiter/', views.waiter_dashboard, name='waiter_dashboard'),
    path('waiter/orders/live/', views.waiter_orders_live, name='waiter_orders_live'),
    path('kitchen/', views.kitchen_dashboard, name='kitchen_dashboard'),
    path('kitchen/orders/live/', views.kitchen_orders_live, name='kitchen_orders_live'),
    path('cashier/', views.cashier_dashboard, name='cashier_dashboard'),
    path('cashier/orders/<int:order_id>/details/', views.cashier_order_details, name='cashier_order_details'),
    path('cashier/cash-desk/', views.cash_desk_dashboard, name='cash_desk_dashboard'),
    path('cashier/scanner/', views.cashier_barcode_scanner, name='cashier_barcode_scanner'),
    path('orders/<int:order_id>/<str:status>/', views.update_order_status, name='update_order_status'),
]
