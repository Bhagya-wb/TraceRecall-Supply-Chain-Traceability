
import csv
from pathlib import Path
from django.conf import settings

from .models import (
    FinishedLot,
    RecallCase,
    MaterialLot,
    ProductionOrder,
    Delivery,
    RecallAction,
)


def detect_exceptions():
    exceptions = []

    project_root = Path(settings.BASE_DIR)

    # 1. Detect missing input material lots
    csv_path = (
        project_root / "output_full_test" / "material_consumptions.csv"
    )
    material_lots_path = (
        project_root / "output_full_test" / "material_lots.csv"
    )

    if csv_path.exists() and material_lots_path.exists():
        with open(
            material_lots_path, newline="", encoding="utf-8-sig"
        ) as file:
            valid_material_lots = {
                row["material_lot_id"]
                for row in csv.DictReader(file)
            }

        with open(
            csv_path, newline="", encoding="utf-8-sig"
        ) as file:
            for row in csv.DictReader(file):
                if row["material_lot_id"] not in valid_material_lots:
                    exceptions.append({
                        "type": "MISSING_INPUT_LOT",
                        "entity_id": row["consumption_id"],
                        "message": (
                            f"Production order: {row['production_order_id']}; "
                            f"Missing material lot: {row['material_lot_id']}"
                        ),
                        "severity": "CRITICAL",
                    })

    # 2. Detect overdelivery
    for lot in FinishedLot.objects.all():
        delivered_quantity = sum(
            lot.deliveries.values_list("quantity", flat=True)
        )

        if delivered_quantity > lot.quantity_produced:
            exceptions.append({
                "type": "OVERDELIVERY",
                "entity_id": lot.finished_lot_id,
                "message": (
                    f"Produced: {lot.quantity_produced}, "
                    f"Delivered: {delivered_quantity}, "
                    f"Excess: {delivered_quantity - lot.quantity_produced}"
                ),
                "severity": "HIGH",
            })

    # 3. Find finished lots affected by recalls
    recalled_finished_ids = set(
        RecallCase.objects.filter(
            trigger_entity_type="FINISHED_LOT"
        ).values_list("trigger_lot_id", flat=True)
    )

    raw_recall_ids = RecallCase.objects.filter(
        trigger_entity_type="RAW"
    ).values_list("trigger_lot_id", flat=True)

    for raw_lot in MaterialLot.objects.filter(
        material_lot_id__in=raw_recall_ids
    ):
        production_orders = ProductionOrder.objects.filter(
            material_consumptions__material_lot=raw_lot
        )

        affected_lots = FinishedLot.objects.filter(
            production_order__in=production_orders
        ).values_list("finished_lot_id", flat=True)

        recalled_finished_ids.update(affected_lots)

    # 4. Detect recalled stock still available
    for lot in FinishedLot.objects.filter(
        finished_lot_id__in=recalled_finished_ids,
        quantity_available__gt=0,
    ).exclude(status="QUARANTINED"):

        exceptions.append({
            "type": "RECALLED_STOCK_AVAILABLE",
            "entity_id": lot.finished_lot_id,
            "message": (
                f"Available quantity: {lot.quantity_available}; "
                f"Status: {lot.status}"
            ),
            "severity": "CRITICAL",
        })

   
    # 5. Detect missing customer notifications
    for recall in RecallCase.objects.all():

        if recall.trigger_entity_type == "RAW":
            affected_deliveries = Delivery.objects.filter(
                finished_lot__production_order__material_consumptions__material_lot__material_lot_id=recall.trigger_lot_id
            )

        elif recall.trigger_entity_type == "FINISHED_LOT":
            affected_deliveries = Delivery.objects.filter(
                finished_lot__finished_lot_id=recall.trigger_lot_id
            )

        else:
            continue

        affected_customer_ids = set(
            affected_deliveries.values_list(
                "customer_id", flat=True
            ).distinct()
        )

        notified_customers = set(
            RecallAction.objects.filter(
                recall_case=recall,
                target_type="CUSTOMER",
                action_type="NOTIFY_CUSTOMER",
                status="SENT",
            ).values_list("target_id", flat=True)
        )

        for customer_id in affected_customer_ids - notified_customers:
            exceptions.append({
                "type": "MISSING_CUSTOMER_NOTIFICATION",
                "entity_id": customer_id,
                "message": (
                    f"Customer {customer_id} has no successful "
                    f"notification for recall {recall.recall_case_id}"
                ),
                "severity": "CRITICAL",
            })

    return exceptions
