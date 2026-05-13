import logging
import re
from pathlib import Path

from django.conf import settings

from .models import Order

logger = logging.getLogger(__name__)
ARABIC_RE = re.compile(r'[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF]')

try:
    import win32print
except ImportError:  # pragma: no cover - depends on host OS/runtime
    win32print = None


def _printer_name():
    configured = getattr(settings, 'THERMAL_PRINTER_NAME', '').strip()
    if configured:
        return configured
    return 'XP-80C'


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


def _logo_file_path():
    configured = getattr(settings, 'THERMAL_RECEIPT_LOGO_PATH', '').strip()
    candidates = []
    if configured:
        configured_path = Path(configured)
        candidates.append(configured_path if configured_path.is_absolute() else Path(settings.BASE_DIR) / configured_path)
    candidates.extend([
        Path(settings.BASE_DIR) / 'static' / 'restaurant' / 'img' / 'logo.png',
        Path(settings.BASE_DIR) / 'static' / 'restaurant' / 'img' / 'logo.jpg',
        Path(settings.BASE_DIR) / 'static' / 'restaurant' / 'img' / 'logo.jpeg',
        Path(settings.BASE_DIR) / 'static' / 'restaurant' / 'img' / 'logo.bmp',
    ])
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def _escpos_raster_logo(logo_path):
    try:
        from PIL import Image
    except ImportError:
        logger.error('Receipt logo skipped: Pillow is not installed.')
        return b''

    image = Image.open(logo_path).convert('L')
    max_width = 384
    if image.width > max_width:
        ratio = max_width / float(image.width)
        image = image.resize((max_width, max(1, int(image.height * ratio))), Image.LANCZOS)
    image = image.point(lambda px: 255 if px > 180 else 0, mode='1')

    return _escpos_raster_image(image)


def _escpos_raster_image(image):
    if image.mode != '1':
        image = image.convert('1')

    width = image.width
    height = image.height
    width_bytes = (width + 7) // 8
    raster = bytearray()
    pixels = image.load()
    for y in range(height):
        for xb in range(width_bytes):
            packed = 0
            for bit in range(8):
                x = xb * 8 + bit
                if x >= width:
                    continue
                if pixels[x, y] == 0:
                    packed |= (1 << (7 - bit))
            raster.append(packed)

    x_low = width_bytes & 0xFF
    x_high = (width_bytes >> 8) & 0xFF
    y_low = height & 0xFF
    y_high = (height >> 8) & 0xFF
    return b'\x1dv0\x00' + bytes([x_low, x_high, y_low, y_high]) + bytes(raster)


def _contains_arabic(text):
    return bool(ARABIC_RE.search(text or ''))


def _shape_receipt_line(text):
    if not _contains_arabic(text):
        return text
    try:
        import arabic_reshaper
        from bidi.algorithm import get_display
    except ImportError:
        logger.error('Arabic shaping packages missing. Install arabic-reshaper and python-bidi.')
        return text
    return get_display(arabic_reshaper.reshape(text))


def _load_receipt_font(font_size=22):
    try:
        from PIL import ImageFont
    except ImportError:
        return None

    def supports_arabic(font):
        try:
            return font.getmask('ت').getbbox() is not None
        except Exception:
            return False

    configured = getattr(settings, 'THERMAL_RECEIPT_FONT_PATH', '').strip()
    candidates = []
    if configured:
        configured_path = Path(configured)
        candidates.append(configured_path if configured_path.is_absolute() else Path(settings.BASE_DIR) / configured_path)
    candidates.extend([
        Path(settings.BASE_DIR) / 'static' / 'restaurant' / 'fonts' / 'NotoNaskhArabic-Regular.ttf',
        Path(settings.BASE_DIR) / 'static' / 'restaurant' / 'fonts' / 'NotoSansArabic-Regular.ttf',
    ])
    candidates.extend([
        Path('C:\\Windows\\Fonts\\arial.ttf'),
        Path('C:\\Windows\\Fonts\\arialuni.ttf'),
        Path('C:\\Windows\\Fonts\\tahoma.ttf'),
        Path('C:\\Windows\\Fonts\\segoeui.ttf'),
        Path('/usr/share/fonts/truetype/noto/NotoNaskhArabic-Regular.ttf'),
        Path('/usr/share/fonts/truetype/noto/NotoSansArabic-Regular.ttf'),
        Path('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'),
    ])

    for font_path in candidates:
        try:
            if font_path.exists():
                font = ImageFont.truetype(str(font_path), font_size)
                if supports_arabic(font):
                    logger.info('Using receipt font: %s', font_path)
                    return font
        except Exception:
            continue
    logger.error('No Arabic-capable receipt font found. Set THERMAL_RECEIPT_FONT_PATH to a TTF that supports Arabic.')
    return None


def _receipt_text_image(lines):
    try:
        from PIL import Image, ImageDraw
    except ImportError:
        logger.error('Receipt text image skipped: Pillow is not installed.')
        return None

    font = _load_receipt_font()
    if font is None:
        return None
    shaped_lines = [_shape_receipt_line(line) for line in lines]
    width = 584
    left_pad = 10
    right_pad = 10
    top_pad = 8
    line_spacing = 8
    bbox = font.getbbox('Ag')
    glyph_height = (bbox[3] - bbox[1]) if bbox else 20
    line_height = glyph_height + line_spacing
    height = top_pad * 2 + max(1, len(shaped_lines)) * line_height
    image = Image.new('1', (width, height), 1)
    draw = ImageDraw.Draw(image)

    y = top_pad
    for raw_line, line in zip(lines, shaped_lines):
        if _contains_arabic(raw_line):
            line_bbox = draw.textbbox((0, 0), line, font=font)
            text_width = (line_bbox[2] - line_bbox[0]) if line_bbox else 0
            x = max(left_pad, int(width - right_pad - text_width))
        else:
            x = left_pad
        draw.text((x, y), line, font=font, fill=0)
        y += line_height
    return image


def _kitchen_ticket_lines(order):
    table_name = str(order.table) if order.table else 'Emporter'
    waiter_name = order.waiter.get_username() if order.waiter else '-'
    lines = [
        'GRILLADE LE GOUT: à la cuisine',
        '==========================================',
        f'KITCHEN ORDER #{order.id}',
        f'Table: {table_name}',
        # f'Waiter: {waiter_name}',
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
    return lines


def _kitchen_ticket_text(order):
    return '\r\n'.join(_kitchen_ticket_lines(order))


def _kitchen_ticket_payload(order):
    lines = _kitchen_ticket_lines(order)
    payload = bytearray(b'\x1b@\n')
    payload.extend(b'\x1ba\x00')
    text_image = _receipt_text_image(lines)
    if text_image is not None:
        payload.extend(_escpos_raster_image(text_image))
    else:
        payload.extend('\r\n'.join(lines).encode('cp437', errors='replace'))
    payload.extend(b'\n\n\n\x1dV\x00')
    return bytes(payload)


def _payment_receipt_payload(order):
    logo_path = _logo_file_path()
    table_name = str(order.table) if order.table else 'Emporter'
    waiter_name = order.waiter.get_username() if order.waiter else 'Caisse'
    subtotal = float(order.total)
    discount = float(order.discount_amount or 0)
    total = float(order.payable_total)

    lines = [
        '==========================================',
        f'PAYMENT RECEIPT #{order.id}',
        f'Table: {table_name}',
        f'Waiter: {waiter_name}',
        f'Time: {order.date.strftime("%Y-%m-%d %H:%M:%S")}',
        '------------------------------------------',
    ]

    for item in order.items.all():
        item_total = float(item.line_total)
        lines.append(f'{item.quantity} x {item.menu_item.name}')
        lines.append(f'   {float(item.unit_price):.2f} x {item.quantity} = {item_total:.2f}')

    lines.extend([
        '------------------------------------------',
        f'Subtotal: {subtotal:.2f} DH',
    ])
    if discount > 0:
        lines.append(f'Discount: -{discount:.2f} DH')
    lines.extend([
        f'Total: {total:.2f} DH',
        '==========================================',
        'Merci pour votre visite !',
        '',
        '',
        '',
    ])

    payload = bytearray(b'\x1b@\n')
    if logo_path:
        payload.extend(b'\x1ba\x01')
        payload.extend(_escpos_raster_logo(logo_path))
        payload.extend(b'\n')
    else:
        payload.extend(b'\x1ba\x01\x1d!\x11')
        payload.extend(b'GRILLADE LE GOUT\n')
        payload.extend(b'\x1d!\x00')
    payload.extend(b'\x1ba\x00')
    text_image = _receipt_text_image(lines)
    if text_image is not None:
        payload.extend(_escpos_raster_image(text_image))
    else:
        payload.extend('\r\n'.join(lines).encode('cp437', errors='replace'))
    payload.extend(b'\n\n\n\x1dV\x00')
    return bytes(payload)


def _print_payload(doc_name, payload):
    printer_name = _resolved_printer_name()
    handle = win32print.OpenPrinter(printer_name)
    try:
        win32print.StartDocPrinter(handle, 1, (doc_name, None, 'RAW'))
        win32print.StartPagePrinter(handle)
        win32print.WritePrinter(handle, payload)
        win32print.EndPagePrinter(handle)
        win32print.EndDocPrinter(handle)
    finally:
        win32print.ClosePrinter(handle)


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
    payload = _kitchen_ticket_payload(order)
    _print_payload(f'Kitchen Order #{order.id}', payload)


def print_payment_receipt(order_id):
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
    payload = _payment_receipt_payload(order)
    _print_payload(f'Payment Receipt #{order.id}', payload)


def dispatch_kitchen_ticket(order_id):
    try:
        print_kitchen_ticket(order_id)
        return True, None
    except Exception as exc:
        logger.exception('Kitchen thermal printing failed for order #%s.', order_id)
        return False, str(exc)


def dispatch_payment_receipt(order_id):
    try:
        print_payment_receipt(order_id)
        return True, None
    except Exception as exc:
        logger.exception('Payment receipt printing failed for order #%s.', order_id)
        return False, str(exc)
