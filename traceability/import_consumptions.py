
import csv
from pathlib import Path
from datetime import datetime
from django.conf import settings

from traceability.models import (
    MaterialConsumption,
    ProductionOrder,
    MaterialLot,
)

CSV_FILE = Path(settings.BASE_DIR) / "output_full_2" / "material_consumptions.csv"

missing = []
imported = 0

with open(CSV_FILE, "r", encoding="utf-8-sig", newline="") as file:
    reader = csv.DictReader(file)

    for row in reader:
        production_order = ProductionOrder.objects.get(
            production_order_id=row["production_order_id"]
        )

        material_lot = MaterialLot.objects.filter(
            material_lot_id=row["material_lot_id"]
        ).first()

        if material_lot is None:
            missing.append(row["material_lot_id"])
            continue

        MaterialConsumption.objects.update_or_create(
            consumption_id=row["consumption_id"],
            defaults={
                "production_order": production_order,
                "material_lot": material_lot,
                "material_id": row["material_id"],
                "quantity_consumed": int(row["quantity_consumed"]),
                "consumed_at": datetime.strptime(
                    row["consumed_at"], "%Y-%m-%d"
                ).date(),
            },
        )

        imported += 1

print("Imported records:", imported)
print("Missing Material Lots:", len(missing))
print("First missing IDs:", missing[:10])
print("Total database records:", MaterialConsumption.objects.count())
