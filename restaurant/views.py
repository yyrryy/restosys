from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Count
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string

from .forms import DiningTableForm, InventoryItemForm, MenuItemForm, OrderCreateForm, RecipeComponentForm
from .models import DiningTable, InventoryItem, MenuItem, Order, OrderItem, UserProfile


def user_role(user):
    if user.is_superuser:
        return UserProfile.ROLE_OWNER
    return getattr(getattr(user, 'profile', None), 'role', UserProfile.ROLE_WAITER)


def dashboard_context(active):
    return {
        'active': active,
        'role': active.title(),
    }


def role_required(*roles):
    def decorator(view_func):
        @wraps(view_func)
        def wrapped(request, *args, **kwargs):
            role = user_role(request.user)
            if role not in roles and role != UserProfile.ROLE_OWNER:
                messages.error(request, 'This dashboard is not available for your account.')
                return redirect('restaurant:dashboard')
            return view_func(request, *args, **kwargs)
        return wrapped
    return decorator


@login_required
def dashboard(request):
    role = user_role(request.user)
    if role == UserProfile.ROLE_OWNER:
        return redirect('restaurant:owner_dashboard')
    if role == UserProfile.ROLE_ADMIN:
        return redirect('restaurant:admin_dashboard')
    if role == UserProfile.ROLE_KITCHEN:
        return redirect('restaurant:kitchen_dashboard')
    if role == UserProfile.ROLE_CASHIER:
        return redirect('restaurant:cashier_dashboard')
    return redirect('restaurant:waiter_dashboard')


def create_order_from_form(form, menu_items, waiter):
    order = Order.objects.create(
        table=form.cleaned_data['table'],
        customer_name=form.cleaned_data['customer_name'],
        waiter=waiter,
        status=Order.STATUS_QUEUED,
    )
    menu_by_id = {item.pk: item for item in menu_items}
    for item_id, quantity in form.selected_items():
        menu_item = menu_by_id[item_id]
        OrderItem.objects.create(
            order=order,
            menu_item=menu_item,
            quantity=quantity,
            unit_price=menu_item.price,
        )
    if order.table:
        order.table.status = DiningTable.STATUS_OCCUPIED
        order.table.save(update_fields=['status'])
    return order


def create_paid_pos_order(form, menu_items):
    selected_waiter = form.cleaned_data.get('cashier_waiter')
    order = create_order_from_form(form, menu_items, selected_waiter)
    success, stock_message = deduct_order_stock(order)
    if not success:
        order.delete()
        return None, stock_message

    order.status = Order.STATUS_PAID
    order.save(update_fields=['status'])
    if order.table:
        order.table.status = DiningTable.STATUS_AVAILABLE
        order.table.save(update_fields=['status'])
    return order, stock_message


def deduct_order_stock(order):
    if order.stock_deducted:
        return True, 'Stock already deducted for this order.'

    required = {}
    for order_item in order.items.select_related('menu_item').prefetch_related('menu_item__components__inventory_item'):
        for component in order_item.menu_item.components.all():
            current = required.get(component.inventory_item_id, {
                'item': component.inventory_item,
                'quantity': 0,
            })
            current['quantity'] += component.quantity * order_item.quantity
            required[component.inventory_item_id] = current

    if not required:
        order.stock_deducted = True
        order.save(update_fields=['stock_deducted'])
        return True, 'No recipe components were configured for this order.'

    with transaction.atomic():
        inventory_items = InventoryItem.objects.select_for_update().filter(id__in=required.keys())
        inventory_by_id = {item.id: item for item in inventory_items}
        shortages = []

        for inventory_id, data in required.items():
            inventory_item = inventory_by_id[inventory_id]
            if inventory_item.quantity < data['quantity']:
                shortages.append(f"{inventory_item.name}: need {data['quantity']} {inventory_item.unit}, have {inventory_item.quantity}")

        # if shortages:
        #     return False, 'Not enough stock. ' + '; '.join(shortages)

        for inventory_id, data in required.items():
            inventory_item = inventory_by_id[inventory_id]
            inventory_item.quantity -= data['quantity']
            inventory_item.save(update_fields=['quantity'])

        order.stock_deducted = True
        order.save(update_fields=['stock_deducted'])

    return True, 'Stock deducted from recipe components.'


@login_required
@role_required(UserProfile.ROLE_OWNER)
def owner_dashboard(request):
    orders = Order.objects.prefetch_related('items')
    paid_total = sum(order.total for order in orders.filter(status=Order.STATUS_PAID))
    context = dashboard_context('owner')
    context.update({
        'stats': [
            {'label': 'Total orders', 'value': orders.count()},
            {'label': 'Active orders', 'value': orders.exclude(status__in=[Order.STATUS_PAID, Order.STATUS_SERVED]).count()},
            {'label': 'Tables', 'value': DiningTable.objects.count()},
            {'label': 'Revenue paid', 'value': paid_total},
        ],
        'orders_by_status': Order.objects.values('status').annotate(total=Count('id')).order_by('status'),
        'low_inventory': [item for item in InventoryItem.objects.all() if item.needs_reorder],
    })
    return render(request, 'restaurant/owner_dashboard.html', context)


@login_required
@role_required(UserProfile.ROLE_ADMIN)
def admin_dashboard(request):
    forms = {
        'table': DiningTableForm(prefix='table'),
        'menu': MenuItemForm(prefix='menu'),
        'inventory': InventoryItemForm(prefix='inventory'),
        'component': RecipeComponentForm(prefix='component'),
    }

    if request.method == 'POST':
        form_type = request.POST.get('form_type')
        if form_type in forms:
            form_class = {
                'table': DiningTableForm,
                'menu': MenuItemForm,
                'inventory': InventoryItemForm,
                'component': RecipeComponentForm,
            }[form_type]
            files = request.FILES if form_type == 'menu' else None
            forms[form_type] = form_class(request.POST, files, prefix=form_type)
            if forms[form_type].is_valid():
                forms[form_type].save()
                messages.success(request, 'Saved successfully.')
                return redirect('restaurant:admin_dashboard')

    context = dashboard_context('admin')
    context.update({
        'forms': forms,
        'tables': DiningTable.objects.all(),
        'menu_items': MenuItem.objects.prefetch_related('components__inventory_item'),
        'inventory_items': InventoryItem.objects.all(),
        'stats': [
            {'label': 'Menu items', 'value': MenuItem.objects.count()},
            {'label': 'Tables', 'value': DiningTable.objects.count()},
            {'label': 'Inventory items', 'value': InventoryItem.objects.count()},
            {'label': 'Orders today', 'value': Order.objects.count()},
        ],
    })
    return render(request, 'restaurant/admin_dashboard.html', context)


@login_required
@role_required(UserProfile.ROLE_ADMIN)
def inventory_dashboard(request):
    inventory_items = InventoryItem.objects.all()
    context = dashboard_context('inventory')
    context.update({
        'inventory_items': inventory_items,
        'stats': [
            {'label': 'Products', 'value': inventory_items.count()},
            {'label': 'Low stock', 'value': len([item for item in inventory_items if item.needs_reorder])},
            {'label': 'Total quantity', 'value': sum(item.quantity for item in inventory_items)},
            {'label': 'Recipe links', 'value': sum(item.recipe_components.count() for item in inventory_items)},
        ],
    })
    return render(request, 'restaurant/inventory_dashboard.html', context)


@login_required
@role_required(UserProfile.ROLE_WAITER, UserProfile.ROLE_CASHIER)
def pos_dashboard(request):
    role = user_role(request.user)
    menu_items = MenuItem.objects.filter(is_available=True)
    is_cashier_mode = role == UserProfile.ROLE_CASHIER
    form = OrderCreateForm(
        request.POST or None,
        menu_items=menu_items,
        require_table=not is_cashier_mode,
        include_waiter_choice=is_cashier_mode,
    )

    if request.method == 'POST' and form.is_valid():
        if not form.selected_items():
            messages.error(request, 'Choose at least one dish before checkout.')
        elif is_cashier_mode:
            order, stock_message = create_paid_pos_order(form, menu_items)
            if order:
                messages.success(request, f'POS order #{order.pk} paid.')
                messages.success(request, stock_message)
                return redirect('restaurant:pos_dashboard')
            messages.error(request, stock_message)
        else:
            order = create_order_from_form(form, menu_items, request.user)
            messages.success(request, f'Order #{order.pk} sent to kitchen.')
            return redirect('restaurant:pos_dashboard')

    context = dashboard_context('pos')
    context.update({
        'form': form,
        'is_cashier_mode': is_cashier_mode,
        'menu_items': menu_items,
        'menu_categories': MenuItem.CATEGORY_CHOICES,
    })
    return render(request, 'restaurant/pos.html', context)


@login_required
@role_required(UserProfile.ROLE_WAITER)
def waiter_dashboard(request):
    context = dashboard_context('waiter')
    context.update({
        'orders': Order.objects.filter(waiter=request.user).prefetch_related('items__menu_item')[:20],
        'ready_orders': Order.objects.filter(waiter=request.user, status=Order.STATUS_READY),
    })
    return render(request, 'restaurant/waiter_dashboard.html', context)


@login_required
@role_required(UserProfile.ROLE_WAITER)
def waiter_orders_live(request):
    orders = Order.objects.filter(waiter=request.user).prefetch_related('items__menu_item')
    ready_orders = Order.objects.filter(waiter=request.user, status=Order.STATUS_READY)
    print('Waiter live orders:', list(orders.values_list('id', 'status')))
    return JsonResponse({
        'orders_html': render_to_string(
            'restaurant/partials/order_table.html',
            {'orders': orders, 'show_actions': True, 'next_url': '/waiter/'},
            request=request,
        ),
        'ready_alerts_html': render_to_string(
            'restaurant/partials/ready_alerts.html',
            {'ready_orders': ready_orders},
            request=request,
        ),
        'ready_count': ready_orders.count(),
        'orders_count': orders.count(),
    })


@login_required
@role_required(UserProfile.ROLE_KITCHEN)
def kitchen_dashboard(request):
    context = dashboard_context('kitchen')
    context.update({
        'orders': Order.objects.exclude(status__in=[Order.STATUS_READY, Order.STATUS_SERVED, Order.STATUS_PAID]).prefetch_related('items__menu_item', 'table'),
        'ready_orders': Order.objects.filter(status=Order.STATUS_READY).prefetch_related('items__menu_item', 'table')[:10],
    })
    return render(request, 'restaurant/kitchen_dashboard.html', context)


@login_required
@role_required(UserProfile.ROLE_KITCHEN)
def kitchen_orders_live(request):
    orders = Order.objects.exclude(status__in=[Order.STATUS_READY, Order.STATUS_SERVED, Order.STATUS_PAID]).prefetch_related('items__menu_item', 'table')
    ready_orders = Order.objects.filter(status=Order.STATUS_READY).prefetch_related('items__menu_item', 'table')[:10]
    return JsonResponse({
        'orders_html': render_to_string(
            'restaurant/partials/order_table.html',
            {'orders': orders, 'kitchen_actions': True, 'next_url': '/kitchen/'},
            request=request,
        ),
        'ready_orders_html': render_to_string(
            'restaurant/partials/order_table.html',
            {'orders': ready_orders},
            request=request,
        ),
        'open_count': orders.count(),
        'ready_count': ready_orders.count(),
    })


@login_required
@role_required(UserProfile.ROLE_CASHIER)
def cashier_dashboard(request):
    payable_statuses = [Order.STATUS_READY, Order.STATUS_SERVED]
    payable_orders = Order.objects.filter(status__in=payable_statuses).prefetch_related('items__menu_item', 'table')
    paid_orders = Order.objects.filter(status=Order.STATUS_PAID).prefetch_related('items__menu_item', 'table')[:20]
    context = dashboard_context('cashier')
    context.update({
        'stats': [
            {'label': 'Awaiting payment', 'value': payable_orders.count()},
            {'label': 'Paid orders', 'value': Order.objects.filter(status=Order.STATUS_PAID).count()},
            {'label': 'Open tables', 'value': DiningTable.objects.exclude(status=DiningTable.STATUS_AVAILABLE).count()},
            {'label': 'Cash collected', 'value': sum(order.total for order in Order.objects.filter(status=Order.STATUS_PAID).prefetch_related('items'))},
        ],
        'payable_orders': payable_orders,
        'paid_orders': paid_orders,
    })
    return render(request, 'restaurant/cashier_dashboard.html', context)


@login_required
def update_order_status(request, order_id, status):
    allowed = {Order.STATUS_PREPARING, Order.STATUS_READY, Order.STATUS_SERVED, Order.STATUS_PAID}
    order = get_object_or_404(Order, pk=order_id)
    if request.method == 'POST' and status in allowed:
        role = user_role(request.user)
        kitchen_status = {Order.STATUS_PREPARING, Order.STATUS_READY}
        waiter_status = {Order.STATUS_SERVED}
        cashier_status = {Order.STATUS_PAID}
        if status in kitchen_status and role not in {UserProfile.ROLE_KITCHEN, UserProfile.ROLE_OWNER}:
            messages.error(request, 'Only kitchen accounts can update kitchen order status.')
            return redirect(request.POST.get('next') or 'restaurant:dashboard')
        if status in waiter_status and role not in {UserProfile.ROLE_WAITER, UserProfile.ROLE_OWNER}:
            messages.error(request, 'Only waiter accounts can close table service orders.')
            return redirect(request.POST.get('next') or 'restaurant:dashboard')
        if status in cashier_status and role not in {UserProfile.ROLE_CASHIER, UserProfile.ROLE_OWNER}:
            messages.error(request, 'Only cashier accounts can mark orders as paid.')
            return redirect(request.POST.get('next') or 'restaurant:dashboard')
        if status == Order.STATUS_SERVED:
            success, stock_message = deduct_order_stock(order)
            if not success:
                messages.error(request, stock_message)
                return redirect(request.POST.get('next') or 'restaurant:dashboard')
        order.status = status
        order.save(update_fields=['status'])
        if status == Order.STATUS_PAID and order.table:
            order.table.status = DiningTable.STATUS_AVAILABLE
            order.table.save(update_fields=['status'])
        messages.success(request, f'Order #{order.pk} marked {order.get_status_display()}.')
        if status == Order.STATUS_SERVED:
            messages.success(request, stock_message)
    return redirect(request.POST.get('next') or 'restaurant:dashboard')
