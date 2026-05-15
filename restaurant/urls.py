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
    path('menu/<int:item_id>/history/', views.menu_item_history, name='menu_item_history'),
    path('menu/<int:item_id>/components/', views.get_components, name='get_components'),
    path('menu/<int:item_id>/components/add/', views.add_component, name='add_component'),
    path('menu/<int:item_id>/components/<int:component_id>/update/', views.update_component, name='update_component'),
    path('menu/<int:item_id>/components/<int:component_id>/delete/', views.delete_component, name='delete_component'),
    path('inventory/', views.inventory_dashboard, name='inventory_dashboard'),
    path('inventory/<int:item_id>/history/', views.inventory_item_history, name='inventory_item_history'),
    path('pos/', views.pos2_dashboard, name='pos_dashboard'),
    path('pos2/', views.pos2_dashboard, name='pos2_dashboard'),
    path('pos2/items/', views.pos2_category_items, name='pos2_category_items'),
    path('pos/resolve-plu/', views.pos_resolve_plu, name='pos_resolve_plu'),
    path('waiter/', views.waiter_dashboard, name='waiter_dashboard'),
    path('waiter/orders/live/', views.waiter_orders_live, name='waiter_orders_live'),
    path('kitchen/', views.kitchen_dashboard, name='kitchen_dashboard'),
    path('kitchen/orders/live/', views.kitchen_orders_live, name='kitchen_orders_live'),
    path('cashier/', views.cashier_dashboard, name='cashier_dashboard'),
    path('cashier/orders/live/', views.cashier_orders_live, name='cashier_orders_live'),
    path('cashier/orders/<int:order_id>/details/', views.cashier_order_details, name='cashier_order_details'),
    path('cashier/orders/<int:order_id>/print/', views.cashier_print_receipt, name='cashier_print_receipt'),
    path('cashier/tables/<int:table_id>/details/', views.cashier_table_details, name='cashier_table_details'),
    path('cashier/tables/<int:table_id>/pay/', views.pay_table_orders, name='pay_table_orders'),
    path('cashier/cash-desk/', views.cash_desk_dashboard, name='cash_desk_dashboard'),
    path('cashier/scanner/', views.cashier_barcode_scanner, name='cashier_barcode_scanner'),
    path('orders/<int:order_id>/<str:status>/', views.update_order_status, name='update_order_status'),
]
