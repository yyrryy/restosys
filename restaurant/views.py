from datetime import timezone
import json
from decimal import Decimal, InvalidOperation
from functools import wraps
from multiprocessing import context

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Count, Sum
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string

from .forms import (
    CashDeskEntryForm,
    DiningTableForm,
    AdminUserCreateForm,
    InventoryItemForm,
    MenuCategoryForm,
    MenuItemForm,
    OrderCreateForm,
    PurchaseForm,
    RecipeComponentForm,
    SupplierForm,
)
from .models import CashDeskEntry, DiningTable, InventoryHistory, InventoryItem, MenuCategory, MenuItem, Order, OrderItem, Purchase, PurchaseItem, Supplier, UserProfile, Scalbarcodescan


def user_role(user):
    if user.is_superuser:
        return UserProfile.ROLE_OWNER
    return getattr(getattr(user, 'profile', None), 'role', UserProfile.ROLE_WAITER)


def dashboard_context(active, user=None):
    role = active.title()
    if user is not None:
        role = user_role(user).title()
    return {
        'active': active,
        'role': role,
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
            previous_quantity = inventory_item.quantity
            inventory_item.quantity -= data['quantity']
            inventory_item.save(update_fields=['quantity'])
            InventoryHistory.objects.create(
                inventory_item=inventory_item,
                source=InventoryHistory.SOURCE_RECIPE_ORDER,
                quantity_change=-data['quantity'],
                quantity_before=previous_quantity,
                quantity_after=inventory_item.quantity,
                reference=f'Order #{order.pk}',
                created_by=order.waiter,
            )

        order.stock_deducted = True
        order.save(update_fields=['stock_deducted'])

    return True, 'Stock deducted from recipe components.'


@login_required
@role_required(UserProfile.ROLE_OWNER)
def owner_dashboard(request):
    orders = Order.objects.prefetch_related('items')
    paid_total = sum(order.total for order in orders.filter(status=Order.STATUS_PAID))
    context = dashboard_context('owner', request.user)
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
    User = get_user_model()
    forms = {
        'table': DiningTableForm(prefix='table'),
        'menu': MenuItemForm(prefix='menu'),
        'inventory': InventoryItemForm(prefix='inventory'),
        'component': RecipeComponentForm(prefix='component'),
        'category': MenuCategoryForm(prefix='category'),
        'user': AdminUserCreateForm(prefix='user'),
    }

    if request.method == 'POST':
        form_type = request.POST.get('form_type')
        if form_type in forms:
            form_class = {
                'table': DiningTableForm,
                'menu': MenuItemForm,
                'inventory': InventoryItemForm,
                'component': RecipeComponentForm,
                'category': MenuCategoryForm,
                'user': AdminUserCreateForm,
            }[form_type]
            files = request.FILES if form_type == 'menu' else None
            forms[form_type] = form_class(request.POST, files, prefix=form_type)
            if forms[form_type].is_valid():
                forms[form_type].save()
                messages.success(request, 'Saved successfully.')
                return redirect('restaurant:admin_dashboard')

    context = dashboard_context('admin', request.user)
    context.update({
        'forms': forms,
        'tables': DiningTable.objects.all(),
        'categories': MenuCategory.objects.all(),
        'users': User.objects.select_related('profile').order_by('username'),
        'menu_items': MenuItem.objects.prefetch_related('components__inventory_item'),
        'inventory_items': InventoryItem.objects.all(),
        'stats': [
            {'label': 'Menu items', 'value': MenuItem.objects.count()},
            {'label': 'Categories', 'value': MenuCategory.objects.count()},
            {'label': 'Tables', 'value': DiningTable.objects.count()},
            {'label': 'Users', 'value': User.objects.count()},
            {'label': 'Inventory items', 'value': InventoryItem.objects.count()},
        ],
    })
    return render(request, 'restaurant/admin_dashboard.html', context)


@login_required
@role_required(UserProfile.ROLE_ADMIN)
def inventory_dashboard(request):
    inventory_items = InventoryItem.objects.all()
    context = dashboard_context('inventory', request.user)
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
@role_required(UserProfile.ROLE_ADMIN)
def inventory_item_history(request, item_id):
    inventory_item = get_object_or_404(InventoryItem, pk=item_id)
    out_from_scal = Scalbarcodescan.objects.filter(inventory_item=inventory_item)
    out_from_orders = OrderItem.objects.filter(menu_item__components__inventory_item=inventory_item, order__status=Order.STATUS_SERVED)
    in_from_purchases = PurchaseItem.objects.filter(inventory_item=inventory_item)
    outs = list(out_from_scal) + list(out_from_orders)
    
    # outs = sorted(
    #         list(out_from_scal) + list(out_from_orders),
    #         key=lambda x: getattr(x, 'scanned_at', None) or getattr(x.order, 'date', None) or timezone.now(),
    #         reverse=True
    #     )
    context = {
        'inventory_item': inventory_item,
        'outs': outs,
        'history_ins': in_from_purchases
    }
    return render(request, 'restaurant/inventory_history.html', context)


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

    context = dashboard_context('pos', request.user)
    menu_categories = list(MenuCategory.objects.values_list('name', 'name'))
    if not menu_categories:
        menu_categories = list(menu_items.values_list('category', 'category').distinct())
    context.update({
        'form': form,
        'is_cashier_mode': is_cashier_mode,
        'menu_items': menu_items,
        'menu_categories': menu_categories,
    })
    return render(request, 'restaurant/pos.html', context)


@login_required
@role_required(UserProfile.ROLE_WAITER, UserProfile.ROLE_CASHIER)
def pos2_dashboard(request):
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
                return redirect('restaurant:pos2_dashboard')
            messages.error(request, stock_message)
        else:
            order = create_order_from_form(form, menu_items, request.user)
            messages.success(request, f'Order #{order.pk} sent to kitchen.')
            return redirect('restaurant:pos2_dashboard')

    context = dashboard_context('pos', request.user)
    menu_categories = list(MenuCategory.objects.values_list('name', 'name'))
    if not menu_categories:
        menu_categories = list(menu_items.values_list('category', 'category').distinct())
    context.update({
        'form': form,
        'is_cashier_mode': is_cashier_mode,
        'menu_categories': menu_categories,
    })
    return render(request, 'restaurant/pos2.html', context)


@login_required
@role_required(UserProfile.ROLE_WAITER, UserProfile.ROLE_CASHIER)
def pos2_category_items(request):
    category = request.GET.get('category', '').strip()
    menu_items = MenuItem.objects.filter(is_available=True)
    if category and category != 'all':
        menu_items = menu_items.filter(category=category)

    items = [
        {
            'id': item.pk,
            'name': item.name,
            'category': item.category,
            'price': float(item.price or 0),
            'display_image': item.display_image,
        }
        for item in menu_items
    ]
    return JsonResponse({'items': items})


@login_required
@role_required(UserProfile.ROLE_WAITER)
def waiter_dashboard(request):
    context = dashboard_context('waiter', request.user)
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
    context = dashboard_context('kitchen', request.user)
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
    paid_orders_queryset = Order.objects.filter(status=Order.STATUS_PAID).prefetch_related('items__menu_item', 'table')
    paid_orders = paid_orders_queryset[:20]
    cash_collected = sum(order.total for order in paid_orders_queryset)
    context = dashboard_context('cashier', request.user)
    context.update({
        'stats': [
            {'label': 'Awaiting payment', 'value': payable_orders.count()},
            {'label': 'Paid orders', 'value': Order.objects.filter(status=Order.STATUS_PAID).count()},
            {'label': 'Open tables', 'value': DiningTable.objects.exclude(status=DiningTable.STATUS_AVAILABLE).count()},
            {'label': 'Cash collected', 'value': cash_collected, 'url': 'restaurant:cash_desk_dashboard'},
        ],
        'payable_orders': payable_orders,
        'paid_orders': paid_orders,
    })
    return render(request, 'restaurant/cashier_dashboard.html', context)


@login_required
@role_required(UserProfile.ROLE_CASHIER)
def cashier_order_details(request, order_id):
    payable_statuses = [Order.STATUS_READY, Order.STATUS_SERVED]
    order = get_object_or_404(
        Order.objects.filter(status__in=payable_statuses).prefetch_related('items__menu_item', 'table'),
        pk=order_id,
    )
    items = [
        {
            'name': item.menu_item.name,
            'quantity': item.quantity,
            'unit_price': float(item.unit_price),
            'line_total': float(item.line_total),
        }
        for item in order.items.all()
    ]
    return JsonResponse({
        'id': order.id,
        'table': str(order.table) if order.table else 'Takeaway',
        'status': order.get_status_display(),
        'total': float(order.total),
        'items': items,
    })


@login_required
@role_required(UserProfile.ROLE_CASHIER)
def cash_desk_dashboard(request):
    form = CashDeskEntryForm(prefix='cashdesk')
    if request.method == 'POST':
        form = CashDeskEntryForm(request.POST, prefix='cashdesk')
        if form.is_valid():
            entry = form.save(commit=False)
            entry.created_by = request.user
            entry.save()
            messages.success(request, f'{entry.get_entry_type_display()} entry saved.')
            return redirect('restaurant:cash_desk_dashboard')

    entries = CashDeskEntry.objects.select_related('created_by')
    in_total = entries.filter(entry_type=CashDeskEntry.TYPE_IN).aggregate(total=Sum('amount'))['total'] or Decimal('0')
    out_total = entries.filter(entry_type=CashDeskEntry.TYPE_OUT).aggregate(total=Sum('amount'))['total'] or Decimal('0')
    paid_orders = Order.objects.filter(status=Order.STATUS_PAID).prefetch_related('items')
    order_cash_total = sum(order.total for order in paid_orders)
    context = dashboard_context('cashier', request.user)
    context.update({
        'form': form,
        'entries': entries[:100],
        'stats': [
            {'label': 'Order cash collected', 'value': order_cash_total},
            {'label': 'Cash in', 'value': in_total},
            {'label': 'Cash out', 'value': out_total},
            {'label': 'Net cash desk', 'value': in_total - out_total},
        ],
    })
    return render(request, 'restaurant/cash_desk_dashboard.html', context)


def parse_scale_barcode(barcode):
    if not barcode:
        return None, 'Scan a barcode first.'
    if not barcode.isdigit() or len(barcode) < 12:
        return None, 'Barcode must contain at least 12 digits.'

    return {
        'raw': barcode,
        'prefix': barcode[:2],
        'plu': int(barcode[2:7]),
        'price': Decimal(int(barcode[7:12])) / Decimal('100'),
    }, None


def process_scale_scan(user, barcode_input):
    parsed_barcode, error = parse_scale_barcode(barcode_input)
    if error:
        return {'ok': False, 'error': error}

    with transaction.atomic():
        try:
            product = InventoryItem.objects.select_for_update().get(plu=parsed_barcode['plu'])
        except InventoryItem.DoesNotExist:
            return {'ok': False, 'error': f'No product found for PLU {parsed_barcode["plu"]}.'}

        if product.price is None or product.price <= 0:
            return {'ok': False, 'error': f'{product.name} has no valid price.'}

        deducted_quantity = round(float(parsed_barcode['price']) / product.price, 3)
        if deducted_quantity <= 0:
            return {'ok': False, 'error': f'Computed quantity is invalid for {product.name}.'}
        if product.quantity < deducted_quantity:
            return {
                'ok': False,
                'error': (
                    f'Not enough stock for {product.name}. Need {deducted_quantity} '
                    f'{product.unit}, have {product.quantity} {product.unit}.'
                ),
            }
        
        previous_quantity = product.quantity
        product.quantity -= deducted_quantity
        product.save(update_fields=['quantity'])

        Scalbarcodescan.objects.create(
            barcode=parsed_barcode['raw'],
            inventory_item=product,
            weight=deducted_quantity,
            price=parsed_barcode['price'],
        )

        InventoryHistory.objects.create(
            inventory_item=product,
            source=InventoryHistory.SOURCE_BARCODE_SCAN,
            quantity_change=-deducted_quantity,
            quantity_before=previous_quantity,
            quantity_after=product.quantity,
            barcode=parsed_barcode['raw'],
            reference=f'PLU {parsed_barcode["plu"]}',
            created_by=user,
        )

    result = {
        'raw': parsed_barcode['raw'],
        'prefix': parsed_barcode['prefix'],
        'plu': parsed_barcode['plu'],
        'price': float(parsed_barcode['price']),
        'product_name': product.name,
        'price_per_kg': float(product.price_per_kg),
        'weight': deducted_quantity,
        'deducted_quantity': deducted_quantity,
        'previous_quantity': previous_quantity,
        'remaining_quantity': product.quantity,
        'unit': product.unit,
    }
    return {
        'ok': True,
        'message': (
            f'Scanned {product.name}: deducted {deducted_quantity} '
            f'{product.unit}. Remaining {product.quantity} {product.unit}.'
        ),
        'result': result,
    }


@login_required
@role_required(UserProfile.ROLE_CASHIER)
def cashier_barcode_scanner(request):
    barcode_input = ''
    barcode_result = None
    if request.method == 'POST':
        barcode_input = request.POST.get('barcode', '').strip()
        scan_response = process_scale_scan(request.user, barcode_input)
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse(scan_response, status=200 if scan_response['ok'] else 400)
        if scan_response['ok']:
            barcode_result = scan_response['result']
            messages.success(request, scan_response['message'])
        else:
            messages.error(request, scan_response['error'])

    context = dashboard_context('cashier', request.user)
    context.update({
        'barcode_input': barcode_input,
        'barcode_result': barcode_result,
    })
    return render(request, 'restaurant/cashier_scanner.html', context)


@login_required
@role_required(UserProfile.ROLE_OWNER, UserProfile.ROLE_ADMIN)
def purchase_item_search(request):
    query = request.GET.get('q', '').strip()
    if len(query) < 1:
        return JsonResponse({'results': []})
    items = InventoryItem.objects.filter(name__icontains=query).values('id', 'name', 'unit')[:15]
    return JsonResponse({'results': list(items)})


def parse_purchase_lines(raw_lines):
    if not raw_lines:
        return [], ['Add at least one product to the purchase.']
    try:
        data = json.loads(raw_lines)
    except json.JSONDecodeError:
        return [], ['Purchase lines are invalid.']
    if not isinstance(data, list) or not data:
        return [], ['Add at least one product to the purchase.']

    cleaned = []
    errors = []
    for index, line in enumerate(data, start=1):
        if not isinstance(line, dict):
            errors.append(f'Line {index} is invalid.')
            continue

        try:
            inventory_item_id = int(line.get('inventory_item_id'))
        except (TypeError, ValueError):
            errors.append(f'Line {index}: select a valid product.')
            continue

        try:
            quantity = Decimal(str(line.get('quantity')))
        except (InvalidOperation, TypeError):
            errors.append(f'Line {index}: quantity is invalid.')
            continue

        try:
            unit_cost = Decimal(str(line.get('unit_cost')))
        except (InvalidOperation, TypeError):
            errors.append(f'Line {index}: price is invalid.')
            continue

        if quantity <= 0:
            errors.append(f'Line {index}: quantity must be greater than zero.')
        if unit_cost < 0:
            errors.append(f'Line {index}: price cannot be negative.')

        cleaned.append({
            'inventory_item_id': inventory_item_id,
            'quantity': quantity,
            'unit_cost': unit_cost,
        })

    if errors:
        return [], errors
    return cleaned, []


@login_required
@role_required(UserProfile.ROLE_OWNER, UserProfile.ROLE_ADMIN)
def suppliers_dashboard(request):
    forms = {'supplier': SupplierForm(prefix='supplier')}
    suppliers = Supplier.objects.all()

    if request.method == 'POST':
        form_type = request.POST.get('form_type')
        if form_type == 'supplier':
            forms['supplier'] = SupplierForm(request.POST, prefix='supplier')
            if forms['supplier'].is_valid():
                forms['supplier'].save()
                messages.success(request, 'Supplier saved successfully.')
                return redirect('restaurant:suppliers_dashboard')

    context = dashboard_context('suppliers', request.user)
    context.update({
        'forms': forms,
        'suppliers': suppliers,
        'stats': [
            {'label': 'Suppliers', 'value': suppliers.count()},
            {'label': 'With phone', 'value': suppliers.exclude(phone='').count()},
            {'label': 'With email', 'value': suppliers.exclude(email='').count()},
            {'label': 'With notes', 'value': suppliers.exclude(notes='').count()},
        ],
    })
    return render(request, 'restaurant/suppliers_dashboard.html', context)


@login_required
@role_required(UserProfile.ROLE_OWNER, UserProfile.ROLE_ADMIN)
def purchase_dashboard(request):
    form = PurchaseForm(prefix='purchase')
    purchase_lines_json = '[]'
    purchase_number_query = request.GET.get('purchase_number', '').strip()

    if request.method == 'POST':
        form = PurchaseForm(request.POST, prefix='purchase')
        purchase_lines_json = request.POST.get('purchase_lines_json', '[]')
        purchase_lines, line_errors = parse_purchase_lines(purchase_lines_json)
        if form.is_valid() and not line_errors:
            line_item_ids = {line['inventory_item_id'] for line in purchase_lines}
            with transaction.atomic():
                inventory_items = InventoryItem.objects.select_for_update().filter(id__in=line_item_ids)
                inventory_by_id = {item.id: item for item in inventory_items}
                if len(inventory_by_id) != len(line_item_ids):
                    messages.error(request, 'One or more selected products no longer exist.')
                else:
                    purchase = form.save(commit=False)
                    purchase.created_by = request.user
                    purchase.save()
                    for line in purchase_lines:
                        inventory_item = inventory_by_id[line['inventory_item_id']]
                        previous_quantity = inventory_item.quantity
                        PurchaseItem.objects.create(
                            purchase=purchase,
                            inventory_item=inventory_item,
                            quantity=line['quantity'],
                            unit_cost=line['unit_cost'],
                        )
                        inventory_item.quantity += line['quantity']
                        inventory_item.save(update_fields=['quantity'])
                        InventoryHistory.objects.create(
                            inventory_item=inventory_item,
                            source=InventoryHistory.SOURCE_PURCHASE,
                            quantity_change=line['quantity'],
                            quantity_before=previous_quantity,
                            quantity_after=inventory_item.quantity,
                            reference=purchase.purchase_number or f'Purchase #{purchase.pk}',
                            created_by=request.user,
                        )
                    messages.success(request, 'Purchase recorded and stock updated.')
                    return redirect('restaurant:purchase_dashboard')
        for error in line_errors:
            messages.error(request, error)

    purchases = Purchase.objects.select_related('supplier', 'created_by').prefetch_related('items__inventory_item')
    if purchase_number_query:
        purchases = purchases.filter(purchase_number__icontains=purchase_number_query)
    context = dashboard_context('purchases', request.user)
    context.update({
        'form': form,
        'purchase_lines_json': purchase_lines_json,
        'purchase_number_query': purchase_number_query,
        'purchases': purchases[:30],
        'stats': [
            {'label': 'Purchases', 'value': purchases.count()},
            {'label': 'Products bought', 'value': PurchaseItem.objects.values('inventory_item').distinct().count()},
            {'label': 'Spend total', 'value': sum(purchase.total_cost for purchase in purchases)},
            {'label': 'Suppliers', 'value': Supplier.objects.count()},
        ],
    })
    return render(request, 'restaurant/purchase_dashboard.html', context)


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
