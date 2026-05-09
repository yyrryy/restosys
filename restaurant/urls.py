from django.urls import path

from . import views

app_name = 'restaurant'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('owner/', views.owner_dashboard, name='owner_dashboard'),
    path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('inventory/', views.inventory_dashboard, name='inventory_dashboard'),
    path('pos/', views.pos_dashboard, name='pos_dashboard'),
    path('waiter/', views.waiter_dashboard, name='waiter_dashboard'),
    path('waiter/orders/live/', views.waiter_orders_live, name='waiter_orders_live'),
    path('kitchen/', views.kitchen_dashboard, name='kitchen_dashboard'),
    path('kitchen/orders/live/', views.kitchen_orders_live, name='kitchen_orders_live'),
    path('cashier/', views.cashier_dashboard, name='cashier_dashboard'),
    path('orders/<int:order_id>/<str:status>/', views.update_order_status, name='update_order_status'),
]
