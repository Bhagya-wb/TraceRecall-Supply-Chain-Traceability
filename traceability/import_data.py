import csv
from pathlib import Path
from datetime import datetime
from django.conf import settings
from traceability.models import RecallCase

CSV_FILE = Path(settings.BASE_DIR) / "output_full_2" / "recall_cases.csv"

with open(CSV_FILE, "r", encoding="utf-8-sig", newline="") as file:
    reader = csv.DictReader(file)

    for row in reader:
        RecallCase.objects.update_or_create(
            recall_case_id=row["recall_case_id"],
            defaults={
                "trigger_entity_type": row["trigger_entity_type"],
                "trigger_lot_id": row["trigger_lot_id"],
                "reason": row["reason"],
                "severity": row["severity"],
                "opened_at": datetime.strptime(
                    row["opened_at"], "%Y-%m-%d"
                ).date(),
                "status": row["status"],
                "scope_delivery_count": int(row["scope_delivery_count"]),
                "scope_quantity": int(row["scope_quantity"]),
            },
        )

print("Recall Cases imported successfully!")
print("Total Recall Cases:", RecallCase.objects.count())