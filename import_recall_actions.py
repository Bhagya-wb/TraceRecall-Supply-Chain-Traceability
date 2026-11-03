
import os
import django
import csv
from pathlib import Path
from datetime import date

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.conf import settings
from traceability.models import RecallAction, RecallCase

csv_path = Path(settings.BASE_DIR) / "output_full_test" / "recall_actions.csv"

created = 0
skipped = 0

with open(csv_path, newline="", encoding="utf-8-sig") as file:
    reader = csv.DictReader(file)

    for row in reader:
        recall = RecallCase.objects.filter(
            recall_case_id=row["recall_case_id"]
        ).first()

        if recall is None:
            skipped += 1
            continue

        action, was_created = RecallAction.objects.get_or_create(
            recall_action_id=row["recall_action_id"],
            defaults={
                "recall_case": recall,
                "action_type": row["action_type"],
                "target_type": row["target_type"],
                "target_id": row["target_id"],
                "action_date": date.fromisoformat(row["action_date"]),
                "status": row["status"],
                "quantity": int(row["quantity"]),
                "notes": row.get("notes", ""),
            },
        )

        if was_created:
            created += 1
        else:
            skipped += 1

print("New actions imported:", created)
print("Rows skipped:", skipped)
print("Total actions in database:", RecallAction.objects.count())
