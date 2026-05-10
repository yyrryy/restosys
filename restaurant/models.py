from django.conf import settings
from django.db import models


class UserProfile(models.Model):
    ROLE_OWNER = 'owner'
    ROLE_ADMIN = 'admin'
    ROLE_WAITER = 'waiter'
    ROLE_KITCHEN = 'kitchen'
    ROLE_CASHIER = 'cashier'

    ROLE_CHOICES = [
        (ROLE_OWNER, 'Owner'),
        (ROLE_ADMIN, 'Admin'),
        (ROLE_WAITER, 'Waiter'),
        (ROLE_KITCHEN, 'Kitchen'),
        (ROLE_CASHIER, 'Cashier'),
    ]

    user = models.OneToOneField(settings.AUTH_USER_MODEL, related_name='profile', on_delete=models.CASCADE)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)

    def __str__(self):
        return f'{self.user.username} ({self.get_role_display()})'


class DiningTable(models.Model):
    STATUS_AVAILABLE = 'available'
    STATUS_OCCUPIED = 'occupied'
    STATUS_RESERVED = 'reserved'
    STATUS_CLEANING = 'cleaning'

    STATUS_CHOICES = [
        (STATUS_AVAILABLE, 'Available'),
        (STATUS_OCCUPIED, 'Occupied'),
        (STATUS_RESERVED, 'Reserved'),
        (STATUS_CLEANING, 'Cleaning'),
    ]

    name = models.CharField(max_length=50, unique=True)
    seats = models.PositiveSmallIntegerField(default=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_AVAILABLE)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class MenuCategory(models.Model):
    name = models.CharField(max_length=60, unique=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class MenuItem(models.Model):
    name = models.CharField(max_length=120)
    category = models.CharField(max_length=60)
    price = models.FloatField(default=0, null=True, blank=True)
    image = models.FileField(upload_to='menu_items/', blank=True)
    is_available = models.BooleanField(default=True)

    class Meta:
        ordering = ['category', 'name']

    def __str__(self):
        return self.name

    @property
    def display_image(self):
        if self.image:
            return self.image.url
        return f'/static/restaurant/img/menu/{self.category}.svg'


class Order(models.Model):
    STATUS_QUEUED = 'queued'
    STATUS_PREPARING = 'preparing'
    STATUS_READY = 'ready'
    STATUS_SERVED = 'served'
    STATUS_PAID = 'paid'

    STATUS_CHOICES = [
        (STATUS_QUEUED, 'Queued'),
        (STATUS_PREPARING, 'Preparing'),
        (STATUS_READY, 'Ready'),
        (STATUS_SERVED, 'Served'),
        (STATUS_PAID, 'Paid'),
    ]

    table = models.ForeignKey(DiningTable, on_delete=models.SET_NULL, null=True, blank=True)
    waiter = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    customer_name = models.CharField(max_length=120, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_QUEUED)
    stock_deducted = models.BooleanField(default=False)
    date = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date']

    def __str__(self):
        source = self.table or self.customer_name or 'Walk-in'
        return f'Order #{self.pk} - {source}'

    @property
    def total(self):
        return sum(item.line_total for item in self.items.all())


class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name='items', on_delete=models.CASCADE)
    menu_item = models.ForeignKey(MenuItem, on_delete=models.PROTECT)
    quantity = models.PositiveSmallIntegerField(default=1)
    unit_price = models.FloatField(default=0)

    def __str__(self):
        return f'{self.quantity} x {self.menu_item}'

    @property
    def line_total(self):
        return self.quantity * self.unit_price


class InventoryItem(models.Model):
    name = models.CharField(max_length=120, unique=True)
    plu = models.PositiveIntegerField(unique=True, null=True, blank=True, db_index=True)
    price = models.FloatField(default=0, null=True, blank=True)
    quantity = models.FloatField(default=0, null=True, blank=True)
    unit = models.CharField(max_length=20, default='unit')
    reorder_level = models.FloatField(default=0, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name

    @property
    def needs_reorder(self):
        return self.quantity <= self.reorder_level

    @property
    def price_per_kg(self):
        return self.price


class InventoryHistory(models.Model):
    SOURCE_BARCODE_SCAN = 'barcode_scan'
    SOURCE_PURCHASE = 'purchase'
    SOURCE_RECIPE_ORDER = 'recipe_order'
    SOURCE_CHOICES = [
        (SOURCE_BARCODE_SCAN, 'Scale barcode scan'),
        (SOURCE_PURCHASE, 'Purchase'),
        (SOURCE_RECIPE_ORDER, 'Order recipe'),
    ]

    inventory_item = models.ForeignKey(InventoryItem, related_name='history_entries', on_delete=models.CASCADE)
    source = models.CharField(max_length=30, choices=SOURCE_CHOICES)
    quantity_change = models.FloatField(default=0, null=True, blank=True)
    quantity_before = models.FloatField(default=0, null=True, blank=True)
    quantity_after = models.FloatField(default=0, null=True, blank=True)
    barcode = models.CharField(max_length=32, blank=True, unique=False)
    reference = models.CharField(max_length=120, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='inventory_history_entries', on_delete=models.SET_NULL, null=True, blank=True)
    date = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date']

    def __str__(self):
        return f'{self.inventory_item} {self.quantity_change} ({self.source})'


class RecipeComponent(models.Model):
    menu_item = models.ForeignKey(MenuItem, related_name='components', on_delete=models.CASCADE)
    inventory_item = models.ForeignKey(InventoryItem, related_name='recipe_components', on_delete=models.PROTECT)
    quantity = models.FloatField(default=0, null=True, blank=True)

    class Meta:
        ordering = ['menu_item__name', 'inventory_item__name']
        unique_together = ('menu_item', 'inventory_item')

    def __str__(self):
        return f'{self.menu_item} uses {self.quantity} {self.inventory_item.unit} {self.inventory_item}'


class Supplier(models.Model):
    name = models.CharField(max_length=120, unique=True)
    contact_person = models.CharField(max_length=120, blank=True)
    phone = models.CharField(max_length=40, blank=True)
    email = models.EmailField(blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class Purchase(models.Model):
    supplier = models.ForeignKey(Supplier, related_name='purchases', on_delete=models.PROTECT)
    purchase_number = models.CharField(max_length=80, db_index=True, blank=True, null=True)
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='purchases_created', on_delete=models.SET_NULL, null=True, blank=True)
    date = models.DateTimeField(auto_now_add=True)
    total = models.FloatField(default=0, null=True, blank=True)
    class Meta:
        ordering = ['-date']

    def __str__(self):
        if self.purchase_number:
            return f'Purchase {self.purchase_number} from {self.supplier}'
        return f'Purchase #{self.pk} from {self.supplier}'

    @property
    def total_cost(self):
        return sum(item.line_total for item in self.items.all())


class PurchaseItem(models.Model):
    purchase = models.ForeignKey(Purchase, related_name='items', on_delete=models.CASCADE)
    inventory_item = models.ForeignKey(InventoryItem, related_name='purchase_items', on_delete=models.PROTECT)
    quantity = models.FloatField(default=0, null=True, blank=True)
    unit_cost = models.FloatField(default=0, null=True, blank=True)
    total = models.FloatField(default=0, null=True, blank=True)

    class Meta:
        ordering = ['inventory_item__name']

    def __str__(self):
        return f'{self.inventory_item} x {self.quantity}'

    @property
    def line_total(self):
        return self.quantity * self.unit_cost


class CashDeskEntry(models.Model):
    TYPE_IN = 'in'
    TYPE_OUT = 'out'
    TYPE_CHOICES = [
        (TYPE_IN, 'Cash In'),
        (TYPE_OUT, 'Cash Out'),
    ]

    entry_type = models.CharField(max_length=3, choices=TYPE_CHOICES)
    amount = models.FloatField(default=0, null=True, blank=True)
    reason = models.CharField(max_length=220, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='cash_desk_entries', on_delete=models.SET_NULL, null=True, blank=True)
    date = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date']

    def __str__(self):
        return f'{self.get_entry_type_display()} {self.amount}'

class Scalbarcodescan(models.Model):
    barcode = models.CharField(max_length=32, unique=False)
    inventory_item = models.ForeignKey(InventoryItem, related_name='barcode_scans', on_delete=models.PROTECT)
    weight = models.FloatField(default=0, null=True, blank=True)
    date = models.DateTimeField(auto_now_add=True)
    price = models.FloatField(default=0, null=True, blank=True)
    class Meta:
        ordering = ['-date']

    def __str__(self):
        return f'Barcode {self.barcode} - {self.inventory_item} ({self.weight} {self.inventory_item.unit})'
    
