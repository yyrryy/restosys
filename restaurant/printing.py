import logging
import os

from django.conf import settings

from .models import Order

logger = logging.getLogger(__name__)

try:
    import win32print
except ImportError:  # pragma: no cover - depends on host OS/runtime
    win32print = None


def _printer_name():
    return "XP-80C"


def _available_printer_names():
    flags = win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS
    return [printer[2] for printer in win32print.EnumPrinters(flags)]


def _resolved_printer_name():
    requested = _printer_name().strip()
    available = _available_printer_names()
    if requested in available:
        return requested

    requested_lower = requested.lower()
    contains_match = next((name for name in available if requested_lower in name.lower()), None)
    if contains_match:
        logger.warning('Using printer "%s" for requested name "%s".', contains_match, requested)
        return contains_match

    default_printer = win32print.GetDefaultPrinter()
    if default_printer in available:
        logger.warning(
            'Requested printer "%s" not found. Falling back to default printer "%s".',
            requested,
            default_printer,
        )
        return default_printer

    raise RuntimeError(f'Thermal printer "{requested}" not found. Available printers: {", ".join(available)}')


def _thermal_printing_enabled():
    return getattr(settings, 'THERMAL_PRINTER_ENABLED', True)


def _kitchen_ticket_text(order):
    table_name = str(order.table) if order.table else 'Takeaway'
    waiter_name = order.waiter.get_username() if order.waiter else '-'
    lines = [
        '==========================================',
        f'KITCHEN ORDER #{order.id}',
        f'Table: {table_name}',
        f'Waiter: {waiter_name}',
        f'Time: {order.date.strftime("%Y-%m-%d %H:%M:%S")}',
        '------------------------------------------',
    ]
    for item in order.items.all():
        lines.append(f'{item.quantity} x {item.menu_item.name}')
    lines.extend([
        '------------------------------------------',
        '',
        '',
        '',
    ])
    return '\r\n'.join(lines)


def print_kitchen_ticket(order_id):
    if not _thermal_printing_enabled():
        return
    if win32print is None:
        logger.error('Thermal printing skipped: win32print is not installed.')
        return

    order = (
        Order.objects
        .select_related('table', 'waiter')
        .prefetch_related('items__menu_item')
        .get(pk=order_id)
    )

    text_payload = _kitchen_ticket_text(order).encode('cp437', errors='replace')
    payload = b'\x1b@\n' + text_payload + b'\n\n\n\x1dV\x00'
    printer_name = _resolved_printer_name()
    handle = win32print.OpenPrinter(printer_name)
    try:
        win32print.StartDocPrinter(handle, 1, (f'Kitchen Order #{order.id}', None, 'RAW'))
        win32print.StartPagePrinter(handle)
        win32print.WritePrinter(handle, payload)
        win32print.EndPagePrinter(handle)
        win32print.EndDocPrinter(handle)
    finally:
        win32print.ClosePrinter(handle)


def dispatch_kitchen_ticket(order_id):
    try:
        print_kitchen_ticket(order_id)
    except Exception:
        logger.exception('Kitchen thermal printing failed for order #%s.', order_id)
