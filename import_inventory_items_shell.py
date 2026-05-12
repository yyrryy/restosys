import json
from pathlib import Path

from django.conf import settings
from restaurant.models import InventoryItem

# Run in Django shell:
# exec(open("import_inventory_items_shell.py", encoding="utf-8").read())

JSON_FILE = Path(settings.BASE_DIR) / "inventory_items.json"
DRY_RUN = False


def to_int(value):
    if value in (None, ""):
        return None
    return int(str(value).strip())


def to_float(value, default=0.0):
    if value in (None, ""):
        return default
    return float(str(value).strip())


rows = json.loads(JSON_FILE.read_text(encoding="utf-8"))

created = 0
updated = 0
skipped = 0

for index, row in enumerate(rows, start=1):
    if not isinstance(row, dict):
        skipped += 1
        print(f"Skipped row {index}: not an object")
        continue

    name = str(row.get("name", "")).strip()
    if not name:
        skipped += 1
        print(f"Skipped row {index}: missing name")
        continue

    plu_value = to_int(row.get("plu"))
    price_value = to_float(row.get("price"), default=0.0)
    reorder_level = to_float(row.get("alert"), default=0.0)
    unit = str(row.get("unit", "unit")).strip() or "unit"

    defaults = {
        "name": name,
        "price": price_value,
        "unit": unit,
        "reorder_level": reorder_level,
    }
    lookup = {"plu": plu_value} if plu_value is not None else {"name": name}
    exists = InventoryItem.objects.filter(**lookup).exists()

    if DRY_RUN:
        print(("Would update" if exists else "Would create") + f": {name} (plu={plu_value})")
        if exists:
            updated += 1
        else:
            created += 1
        continue

    item, was_created = InventoryItem.objects.update_or_create(defaults=defaults, **lookup)
    if was_created:
        created += 1
        print(f"Created: {item.name} (plu={item.plu})")
    else:
        updated += 1
        print(f"Updated: {item.name} (plu={item.plu})")

print(f"Done. Created: {created}, Updated: {updated}, Skipped: {skipped}")
