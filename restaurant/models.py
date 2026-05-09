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


class MenuItem(models.Model):
    CATEGORY_STARTER = 'starter'
    CATEGORY_MAIN = 'main'
    CATEGORY_DESSERT = 'dessert'
    CATEGORY_DRINK = 'drink'

    CATEGORY_CHOICES = [
        (CATEGORY_STARTER, 'Starter'),
        (CATEGORY_MAIN, 'Main'),
        (CATEGORY_DESSERT, 'Dessert'),
        (CATEGORY_DRINK, 'Drink'),
    ]

    name = models.CharField(max_length=120)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    price = models.DecimalField(max_digits=8, decimal_places=2)
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
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

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
    unit_price = models.DecimalField(max_digits=8, decimal_places=2)

    def __str__(self):
        return f'{self.quantity} x {self.menu_item}'

    @property
    def line_total(self):
        return self.quantity * self.unit_price


class InventoryItem(models.Model):
    name = models.CharField(max_length=120, unique=True)
    quantity = models.DecimalField(max_digits=9, decimal_places=2)
    unit = models.CharField(max_length=20, default='unit')
    reorder_level = models.DecimalField(max_digits=9, decimal_places=2, default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name

    @property
    def needs_reorder(self):
        return self.quantity <= self.reorder_level


class RecipeComponent(models.Model):
    menu_item = models.ForeignKey(MenuItem, related_name='components', on_delete=models.CASCADE)
    inventory_item = models.ForeignKey(InventoryItem, related_name='recipe_components', on_delete=models.PROTECT)
    quantity = models.DecimalField(max_digits=9, decimal_places=2)

    class Meta:
        ordering = ['menu_item__name', 'inventory_item__name']
        unique_together = ('menu_item', 'inventory_item')

    def __str__(self):
        return f'{self.menu_item} uses {self.quantity} {self.inventory_item.unit} {self.inventory_item}'
