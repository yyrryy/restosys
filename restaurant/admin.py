from django.contrib import admin

from .models import DiningTable, InventoryHistory, InventoryItem, MenuCategory, MenuItem, Order, OrderItem, Purchase, PurchaseItem, RecipeComponent, Stockout, Supplier, UserProfile, Config


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
    list_display = ('name', 'categoryname', 'price', 'is_available', 'plu')
    list_filter = ('categoryname', 'is_available')
    search_fields = ('name',)


@admin.register(MenuCategory)
class MenuCategoryAdmin(admin.ModelAdmin):
    list_display = ('name',)
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
    list_display = ('id', 'table', 'waiter', 'customer_name', 'status', 'date')
    list_filter = ('status', 'date')
    search_fields = ('customer_name', 'table__name', 'waiter__username')
    inlines = [OrderItemInline]


@admin.register(InventoryItem)
class InventoryItemAdmin(admin.ModelAdmin):
    list_display = ('name', 'plu', 'price', 'quantity', 'unit', 'reorder_level', 'needs_reorder')
    search_fields = ('name', 'plu')


@admin.register(InventoryHistory)
class InventoryHistoryAdmin(admin.ModelAdmin):
    list_display = ('inventory_item', 'source', 'quantity_change', 'quantity_before', 'quantity_after', 'reference', 'created_by', 'date')
    list_filter = ('source', 'date')
    search_fields = ('inventory_item__name', 'barcode', 'reference')


@admin.register(Stockout)
class StockoutAdmin(admin.ModelAdmin):
    list_display = ('inventory_item', 'quantity', 'reason', 'reference', 'created_by', 'date')
    list_filter = ('date',)
    search_fields = ('inventory_item__name', 'reason', 'reference')


@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ('name', 'contact_person', 'phone', 'email')
    search_fields = ('name', 'contact_person', 'phone', 'email')


@admin.register(Purchase)
class PurchaseAdmin(admin.ModelAdmin):
    list_display = ('id', 'purchase_number', 'supplier', 'total_cost', 'created_by', 'date')
    list_filter = ('supplier', 'date')
    search_fields = ('purchase_number', 'supplier__name')


@admin.register(PurchaseItem)
class PurchaseItemAdmin(admin.ModelAdmin):
    list_display = ('purchase', 'inventory_item', 'quantity', 'unit_cost')
    list_filter = ('inventory_item',)
    search_fields = ('purchase__supplier__name', 'inventory_item__name')

@admin.register(Config)
class ConfigAdmin(admin.ModelAdmin):
    list_display = ('serverip',)
    search_fields = ('serverip',)