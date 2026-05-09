from django.contrib import admin

from .models import DiningTable, InventoryItem, MenuItem, Order, OrderItem, RecipeComponent, UserProfile


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'role')
    list_filter = ('role',)
    search_fields = ('user__username',)


@admin.register(DiningTable)
class DiningTableAdmin(admin.ModelAdmin):
    list_display = ('name', 'seats', 'status')
    list_filter = ('status',)
    search_fields = ('name',)


@admin.register(MenuItem)
class MenuItemAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'price', 'is_available')
    list_filter = ('category', 'is_available')
    search_fields = ('name',)


@admin.register(RecipeComponent)
class RecipeComponentAdmin(admin.ModelAdmin):
    list_display = ('menu_item', 'inventory_item', 'quantity')
    list_filter = ('menu_item', 'inventory_item')
    search_fields = ('menu_item__name', 'inventory_item__name')


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 1


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'table', 'waiter', 'customer_name', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('customer_name', 'table__name', 'waiter__username')
    inlines = [OrderItemInline]


@admin.register(InventoryItem)
class InventoryItemAdmin(admin.ModelAdmin):
    list_display = ('name', 'quantity', 'unit', 'reorder_level', 'needs_reorder')
    search_fields = ('name',)
