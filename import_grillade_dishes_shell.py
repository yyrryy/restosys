import json
from pathlib import Path

from restaurant.models import MenuCategory, MenuItem

# Run in Django shell:
# exec(open("import_grillade_dishes_shell.py", encoding="utf-8").read())

JSON_FILE = Path("grillade_dishes.json")
DRY_RUN = False
DEFAULT_CATEGORY = "Grillade"


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

    category = DEFAULT_CATEGORY
    raw_category_id = row.get("category_id")
    if raw_category_id not in (None, ""):
        try:
            category_id = int(raw_category_id)
            category = (
                MenuCategory.objects.filter(pk=category_id)
                .values_list("name", flat=True)
                .first()
                or DEFAULT_CATEGORY
            )
        except (TypeError, ValueError):
            pass

    defaults = {
        "category": category,
        "price": to_float(row.get("price"), default=0.0),
        "is_available": True,
    }

    if DRY_RUN:
        exists = MenuItem.objects.filter(name=name).exists()
        print(("Would update" if exists else "Would create") + f": {name}")
        if exists:
            updated += 1
        else:
            created += 1
        continue

    item, was_created = MenuItem.objects.update_or_create(name=name, defaults=defaults)
    if was_created:
        created += 1
        print(f"Created: {item.name}")
    else:
        updated += 1
        print(f"Updated: {item.name}")

print(f"Done. Created: {created}, Updated: {updated}, Skipped: {skipped}")
