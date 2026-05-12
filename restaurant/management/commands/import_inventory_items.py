import json
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from restaurant.models import InventoryItem


class Command(BaseCommand):
    help = 'Import inventory items from inventory_items.json into InventoryItem.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--file',
            default=str(Path(settings.BASE_DIR) / 'inventory_items.json'),
            help='Path to JSON file (default: <project_root>/inventory_items.json)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Parse and validate items without saving to database.',
        )

    def handle(self, *args, **options):
        file_path = Path(options['file'])
        dry_run = options['dry_run']
        if not file_path.exists():
            raise CommandError(f'File not found: {file_path}')

        try:
            rows = json.loads(file_path.read_text(encoding='utf-8'))
        except json.JSONDecodeError as exc:
            raise CommandError(f'Invalid JSON: {exc}') from exc

        if not isinstance(rows, list):
            raise CommandError('Expected a JSON array of items.')

        created = 0
        updated = 0
        skipped = 0

        for index, row in enumerate(rows, start=1):
            if not isinstance(row, dict):
                skipped += 1
                self.stdout.write(self.style.WARNING(f'Skipped row {index}: not an object'))
                continue

            name = str(row.get('name', '')).strip()
            if not name:
                skipped += 1
                self.stdout.write(self.style.WARNING(f'Skipped row {index}: missing name'))
                continue

            plu_value = self._to_int(row.get('plu'))
            price_value = self._to_float(row.get('price'), default=0.0)
            reorder_level = self._to_float(row.get('alert'), default=0.0)
            unit = str(row.get('unit', 'unit')).strip() or 'unit'

            defaults = {
                'name': name,
                'price': price_value,
                'unit': unit,
                'reorder_level': reorder_level,
            }

            lookup = {'plu': plu_value} if plu_value is not None else {'name': name}
            exists = InventoryItem.objects.filter(**lookup).exists()

            if dry_run:
                action = 'Would update' if exists else 'Would create'
                self.stdout.write(f'{action}: {name} (plu={plu_value}, price={price_value}, unit={unit})')
                if exists:
                    updated += 1
                else:
                    created += 1
                continue

            item, was_created = InventoryItem.objects.update_or_create(defaults=defaults, **lookup)
            if was_created:
                created += 1
                self.stdout.write(self.style.SUCCESS(f'Created: {item.name} (plu={item.plu})'))
            else:
                updated += 1
                self.stdout.write(f'Updated: {item.name} (plu={item.plu})')

        summary = f'Import finished. Created: {created}, Updated: {updated}, Skipped: {skipped}'
        self.stdout.write(self.style.SUCCESS(summary))

    @staticmethod
    def _to_int(value):
        if value in (None, ''):
            return None
        return int(str(value).strip())

    @staticmethod
    def _to_float(value, default=0.0):
        if value in (None, ''):
            return default
        return float(str(value).strip())
