
#!/usr/bin/env python3
"""
TraceRecall - Supply Chain Traceability and Recall Dataset Generator
Deterministic synthetic dataset with four labelled exception scenarios.
"""

import argparse
import csv
import json
import hashlib
import random

from pathlib import Path
from collections import defaultdict
from datetime import date, timedelta

SEED = 20261022

TABLE_FIELDS = {
    "suppliers": [
        "supplier_id", "supplier_name", "country", "risk_tier", "status"
    ],
    "material_lots": [
        "material_lot_id", "supplier_id", "material_id",
        "received_date", "quantity_received", "quantity_available",
        "unit", "status"
    ],
    "products": [
        "product_id", "product_name", "category", "unit"
    ],
    "boms": [
        "bom_id", "product_id", "material_id",
        "quantity_per_unit", "effective_from", "effective_to", "revision"
    ],
    "production_orders": [
        "production_order_id", "product_id", "bom_id",
        "planned_quantity", "actual_quantity", "planned_start",
        "actual_start", "actual_end", "status"
    ],
    "material_consumptions": [
        "consumption_id", "production_order_id", "material_lot_id",
        "material_id", "quantity_consumed", "consumed_at"
    ],
    "finished_lots": [
        "finished_lot_id", "production_order_id", "product_id",
        "manufactured_date", "quantity_produced",
        "quantity_available", "status"
    ],
    "shipments": [
        "shipment_id", "carrier_name", "warehouse_id",
        "dispatch_date", "status"
    ],
    "shipment_lots": [
        "shipment_lot_id", "shipment_id",
        "finished_lot_id", "quantity_shipped"
    ],
    "customers": [
        "customer_id", "customer_name", "customer_type", "country"
    ],
    "deliveries": [
        "delivery_id", "shipment_id", "finished_lot_id",
        "customer_id", "delivery_date", "quantity_delivered", "status"
    ],
    "recall_cases": [
        "recall_case_id", "trigger_entity_type", "trigger_lot_id",
        "reason", "severity", "opened_at", "status",
        "scope_delivery_count", "scope_quantity"
    ],
    "recall_actions": [
        "recall_action_id", "recall_case_id", "action_type",
        "target_type", "target_id", "action_date",
        "status", "quantity", "notes"
    ],
    "state_events": [
        "event_id", "entity_type", "entity_id",
        "from_state", "to_state", "event_time", "reason"
    ]
}


def iso(value):
    return value.isoformat()


def write_csv(path, rows, fields):
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def generate(out, scale, seed):

    rng = random.Random(seed)

    if scale == "starter":
        n_sup = 50
        n_raw = 500
        n_wo = 250
        n_fin = 400
        n_del = 1000
        n_customers = 100
        n_shipments = 200
    else:
        n_sup = 500
        n_raw = 10000
        n_wo = 5000
        n_fin = 8000
        n_del = 20000
        n_customers = 2000
        n_shipments = 4000

    out.mkdir(parents=True, exist_ok=True)

    today = date(2026, 10, 22)

    countries = [
        "India", "USA", "Germany",
        "UK", "Singapore", "Japan"
    ]

    materials = [
        f"MAT-{i:03d}" for i in range(1, 21)
    ]

    products = []

    for i in range(1, 21):
        products.append({
            "product_id": f"PROD-{i:03d}",
            "product_name": f"Finished Product {i:03d}",
            "category": ["Electronics", "Medical Device",
                         "Industrial"][i % 3],
            "unit": "EA"
        })

    suppliers = []

    for i in range(1, n_sup + 1):
        suppliers.append({
            "supplier_id": f"SUP-{i:04d}",
            "supplier_name": f"Supplier {i:04d}",
            "country": rng.choice(countries),
            "risk_tier": rng.choice(["LOW", "MEDIUM", "HIGH"]),
            "status": "ACTIVE"
        })

    customers = []

    for i in range(1, n_customers + 1):
        customers.append({
            "customer_id": f"CUST-{i:05d}",
            "customer_name": f"Customer {i:05d}",
            "customer_type": rng.choice([
                "DISTRIBUTOR", "RETAILER",
                "HOSPITAL", "MANUFACTURER"
            ]),
            "country": rng.choice(countries)
        })

    boms = []
    bom_by_product = {}

    for i, product in enumerate(products, 1):

        bom_id = f"BOM-{i:03d}-R01"

        material1 = materials[(i - 1) % 20]
        material2 = materials[(i + 6) % 20]

        boms.extend([
            {
                "bom_id": bom_id,
                "product_id": product["product_id"],
                "material_id": material1,
                "quantity_per_unit": 1.0,
                "effective_from": "2026-01-01",
                "effective_to": "",
                "revision": "R01"
            },
            {
                "bom_id": bom_id,
                "product_id": product["product_id"],
                "material_id": material2,
                "quantity_per_unit": 0.5,
                "effective_from": "2026-01-01",
                "effective_to": "",
                "revision": "R01"
            }
        ])

        bom_by_product[product["product_id"]] = (
            bom_id, material1, material2
        )


    # Generate raw material lots
    raw_lots = []
    raw_by_material = defaultdict(list)

    for i in range(1, n_raw + 1):

        supplier = suppliers[(i - 1) % n_sup]
        material = materials[(i - 1) % len(materials)]

        lot = {
            "material_lot_id": (
                f"RAWLOT-{supplier['supplier_id']}-2026-{i:06d}"
            ),
            "supplier_id": supplier["supplier_id"],
            "material_id": material,
            "received_date": iso(
                today - timedelta(days=rng.randint(30, 300))
            ),
            "quantity_received": rng.randint(5000, 15000),
            "quantity_available": 0,
            "unit": "EA",
            "status": "RECEIVED"
        }

        lot["quantity_available"] = lot["quantity_received"]

        raw_lots.append(lot)
        raw_by_material[material].append(lot)

    # Generate production orders and material consumption
    production_orders = []
    consumptions = []
    finished_lots = []

    raw_cursor = defaultdict(int)
    raw_consumed = defaultdict(int)
    order_finished = defaultdict(list)

    for i in range(1, n_wo + 1):

        product = products[(i - 1) % len(products)]

        bom_id, material1, material2 = (
            bom_by_product[product["product_id"]]
        )

        qty = rng.randint(300, 900)

        start = today - timedelta(days=rng.randint(10, 180))
        end = start + timedelta(days=rng.randint(1, 4))

        wo_id = f"WO-2026-{i:06d}"

        production_orders.append({
            "production_order_id": wo_id,
            "product_id": product["product_id"],
            "bom_id": bom_id,
            "planned_quantity": qty,
            "actual_quantity": qty,
            "planned_start": iso(start),
            "actual_start": iso(start),
            "actual_end": iso(end),
            "status": "COMPLETED"
        })

        # Consume the required raw materials
        for material, need in [
            (material1, qty),
            (material2, qty * 0.5)
        ]:

            pool = raw_by_material[material]

            lot = pool[
                raw_cursor[material] % len(pool)
            ]

            raw_cursor[material] += 1

            consumed = int(need)

            raw_consumed[lot["material_lot_id"]] += consumed

            consumptions.append({
                "consumption_id": f"CON-{len(consumptions)+1:07d}",
                "production_order_id": wo_id,
                "material_lot_id": lot["material_lot_id"],
                "material_id": material,
                "quantity_consumed": consumed,
                "consumed_at": iso(end)
            })

        # Split production output into finished lots
        n_parts = 2 if i <= (n_fin - n_wo) else 1

        remaining = qty

        for j in range(n_parts):

            part_qty = remaining // (n_parts - j)
            remaining -= part_qty

            fin_id = f"FINLOT-{len(finished_lots)+1:06d}"

            finished_lot = {
                "finished_lot_id": fin_id,
                "production_order_id": wo_id,
                "product_id": product["product_id"],
                "manufactured_date": iso(end),
                "quantity_produced": part_qty,
                "quantity_available": part_qty,
                "status": "AVAILABLE"
            }

            finished_lots.append(finished_lot)
            order_finished[wo_id].append(fin_id)

    # Calculate remaining raw material quantities
    for lot in raw_lots:

        consumed = raw_consumed[lot["material_lot_id"]]

        lot["quantity_available"] = (
            lot["quantity_received"] - consumed
        )

        if lot["quantity_available"] == 0:
            lot["status"] = "DEPLETED"
        elif consumed > 0:
            lot["status"] = "PARTIALLY_CONSUMED"
        else:
            lot["status"] = "AVAILABLE"

    # Generate shipments
    shipments = []

    for i in range(1, n_shipments + 1):

        dispatch = today - timedelta(days=rng.randint(1, 90))

        shipments.append({
            "shipment_id": f"SHP-2026-{i:06d}",
            "carrier_name": rng.choice([
                "BlueDart", "DHL", "FedEx",
                "Delhivery", "UPS"
            ]),
            "warehouse_id": f"WH-{rng.randint(1, 12):02d}",
            "dispatch_date": iso(dispatch),
            "status": "DELIVERED"
        })

    # Generate baseline deliveries without accidental overdelivery
    deliveries = []
    fin_by_id = {
        lot["finished_lot_id"]: lot
        for lot in finished_lots
    }

    shipped_by_fin = defaultdict(int)

    for i in range(n_del):

        fin = finished_lots[i % len(finished_lots)]

        fin_id = fin["finished_lot_id"]

        available = (
            fin["quantity_produced"] - shipped_by_fin[fin_id]
        )

        if available <= 0:
            continue

        qty = min(rng.randint(1, 5), available)

        shipped_by_fin[fin_id] += qty

        shipment_idx = i % n_shipments

        shipment_id = (
            f"SHP-2026-{shipment_idx+1:06d}"
        )

        delivery_date = (
            today - timedelta(days=rng.randint(0, 60))
        )

        deliveries.append({
            "delivery_id": f"DEL-{len(deliveries)+1:07d}",
            "shipment_id": shipment_id,
            "finished_lot_id": fin_id,
            "customer_id": customers[i % len(customers)]["customer_id"],
            "delivery_date": iso(delivery_date),
            "quantity_delivered": qty,
            "status": "DELIVERED"
        })

    # Aggregate shipment quantities by shipment and finished lot
    ship_fin_qty = defaultdict(int)

    for delivery in deliveries:
        key = (
            delivery["shipment_id"],
            delivery["finished_lot_id"]
        )
        ship_fin_qty[key] += delivery["quantity_delivered"]

    shipment_lots = []

    for idx, ((shipment_id, finished_lot_id), qty) in enumerate(
        sorted(ship_fin_qty.items()), 1
    ):
        shipment_lots.append({
            "shipment_lot_id": f"SL-{idx:07d}",
            "shipment_id": shipment_id,
            "finished_lot_id": finished_lot_id,
            "quantity_shipped": qty
        })

    # Identify contaminated raw material lots
    planted_raw = [
        raw_lots[min(7, len(raw_lots) - 1)]["material_lot_id"],
        raw_lots[min(31, len(raw_lots) - 1)]["material_lot_id"]
    ]

    # Trace raw material lots to finished lots
    raw_to_fin = defaultdict(set)

    for consumption in consumptions:
        for finished_id in order_finished[
            consumption["production_order_id"]
        ]:
            raw_to_fin[consumption["material_lot_id"]].add(
                finished_id
            )

    # Select one contaminated finished lot
    planted_fin = [
        finished_lots[min(18, len(finished_lots) - 1)][
            "finished_lot_id"
        ]
    ]

    contaminated_fin = set(planted_fin)

    for raw_id in planted_raw:
        contaminated_fin.update(raw_to_fin[raw_id])

    # Prepare delivery lookup by finished lot
    delivery_by_fin = defaultdict(list)

    for delivery in deliveries:
        delivery_by_fin[delivery["finished_lot_id"]].append(
            delivery
        )

    # Recall records and evaluation labels
    recall_cases = []
    recall_actions = []
    state_events = []
    ground_truth = []

    trigger_specs = (
        [("RAW", lot_id) for lot_id in planted_raw]
        + [("FINISHED", lot_id) for lot_id in planted_fin]
    )

    # Select one customer whose notification will be missing
    first_trigger_type, first_trigger_id = trigger_specs[0]

    first_affected_fin = (
        set(raw_to_fin[first_trigger_id])
        if first_trigger_type == "RAW"
        else {first_trigger_id}
    )

    first_affected_deliveries = [
        delivery
        for finished_id in sorted(first_affected_fin)
        for delivery in delivery_by_fin.get(finished_id, [])
    ]

    first_affected_customers = sorted({
        delivery["customer_id"]
        for delivery in first_affected_deliveries
    })

    missed_customer_id = (
        first_affected_customers[0]
        if first_affected_customers else None
    )

    missed_customer_case_id = "REC-2026-000001"

    # Select one affected finished lot that will remain available
    quarantine_candidates = sorted(contaminated_fin)

    unquarantined_fin_id = (
        quarantine_candidates[0]
        if quarantine_candidates else None
    )

    # Create recall cases and actions
    for index, (entity_type, lot_id) in enumerate(
        trigger_specs, 1
    ):

        recall_id = f"REC-2026-{index:06d}"

        if entity_type == "RAW":
            affected_finished = set(raw_to_fin[lot_id])
        else:
            affected_finished = {lot_id}

        affected_deliveries = [
            delivery
            for finished_id in sorted(affected_finished)
            for delivery in delivery_by_fin.get(finished_id, [])
        ]

        scope_quantity = sum(
            delivery["quantity_delivered"]
            for delivery in affected_deliveries
        )

        recall_cases.append({
            "recall_case_id": recall_id,
            "trigger_entity_type": entity_type,
            "trigger_lot_id": lot_id,
            "reason": "SYNTHETIC_CONTAMINATION",
            "severity": "CRITICAL",
            "opened_at": iso(today),
            "status": "IN_PROGRESS",
            "scope_delivery_count": len(affected_deliveries),
            "scope_quantity": scope_quantity
        })

        # Notify downstream customers.
        affected_customers = sorted({
            delivery["customer_id"]
            for delivery in affected_deliveries
        })

        for customer_id in affected_customers:

            # Deliberately omit one customer's notification.
            if (
                recall_id == missed_customer_case_id
                and customer_id == missed_customer_id
            ):
                continue

            recall_actions.append({
                "recall_action_id": (
                    f"ACT-{len(recall_actions)+1:08d}"
                ),
                "recall_case_id": recall_id,
                "action_type": "NOTIFY_CUSTOMER",
                "target_type": "CUSTOMER",
                "target_id": customer_id,
                "action_date": iso(today),
                "status": "SENT",
                "quantity": 0,
                "notes": "Customer recall notice sent"
            })

        # Create recovery requests for affected deliveries.
        for delivery in affected_deliveries:

            recall_actions.append({
                "recall_action_id": (
                    f"ACT-{len(recall_actions)+1:08d}"
                ),
                "recall_case_id": recall_id,
                "action_type": "RECOVER",
                "target_type": "DELIVERY",
                "target_id": delivery["delivery_id"],
                "action_date": iso(today),
                "status": "PENDING",
                "quantity": delivery["quantity_delivered"],
                "notes": "Awaiting customer return confirmation"
            })

        # Quarantine affected inventory.
        for finished_id in sorted(affected_finished):

            finished = fin_by_id[finished_id]

            # Deliberately leave one recalled lot available for sale.
            if finished_id == unquarantined_fin_id:
                continue

            finished["status"] = "QUARANTINED"
            finished["quantity_available"] = 0

            recall_actions.append({
                "recall_action_id": (
                    f"ACT-{len(recall_actions)+1:08d}"
                ),
                "recall_case_id": recall_id,
                "action_type": "QUARANTINE",
                "target_type": "FINISHED_LOT",
                "target_id": finished_id,
                "action_date": iso(today),
                "status": "COMPLETED",
                "quantity": finished["quantity_produced"],
                "notes": "Inventory successfully quarantined"
            })

            state_events.append({
                "event_id": f"EVT-{len(state_events)+1:08d}",
                "entity_type": "FINISHED_LOT",
                "entity_id": finished_id,
                "from_state": "AVAILABLE",
                "to_state": "QUARANTINED",
                "event_time": iso(today),
                "reason": recall_id
            })

    # Add ground-truth labels for contamination triggers.
    for entity_type, lot_id in trigger_specs:

        if entity_type == "RAW":
            affected_finished = set(raw_to_fin[lot_id])
        else:
            affected_finished = {lot_id}

        affected_deliveries = [
            delivery
            for finished_id in sorted(affected_finished)
            for delivery in delivery_by_fin.get(finished_id, [])
        ]

        ground_truth.append({
            "label_id": f"GT-{len(ground_truth)+1:05d}",
            "label_type": "CONTAMINATED_SOURCE_LOT",
            "entity_type": entity_type,
            "entity_id": lot_id,
            "expected_affected_finished_lots": len(
                affected_finished
            ),
            "expected_affected_deliveries": len(
                affected_deliveries
            ),
            "expected_scope_quantity": sum(
                delivery["quantity_delivered"]
                for delivery in affected_deliveries
            ),
            "rule": (
                "All downstream finished lots and deliveries "
                "from a contaminated source lot are in recall scope."
            )
        })

    # --------------------------------------------------
    # EXCEPTION 1: Missing input material lot reference
    # --------------------------------------------------

    bad_finished_lot = finished_lots[-1]

    bad_consumption_id = f"CON-{len(consumptions)+1:07d}"

    consumptions.append({
        "consumption_id": bad_consumption_id,
        "production_order_id": bad_finished_lot["production_order_id"],
        "material_lot_id": "RAWLOT-MISSING-2026-999999",
        "material_id": "MAT-999",
        "quantity_consumed": 1,
        "consumed_at": iso(today)
    })

    ground_truth.append({
        "label_id": f"GT-{len(ground_truth)+1:05d}",
        "label_type": "ANOMALY_MISSING_INPUT_LOT",
        "entity_type": "FINISHED_LOT",
        "entity_id": bad_finished_lot["finished_lot_id"],
        "expected_result": "FAIL_FOREIGN_KEY",
        "rule": "A production consumption references a nonexistent material lot."
    })

    # --------------------------------------------------
    # EXCEPTION 2: Delivery quantity exceeds production
    # --------------------------------------------------

    over_finished_lot = finished_lots[0]

    over_delivery_id = f"DEL-{len(deliveries)+1:07d}"

    deliveries.append({
        "delivery_id": over_delivery_id,
        "shipment_id": shipments[0]["shipment_id"],
        "finished_lot_id": over_finished_lot["finished_lot_id"],
        "customer_id": customers[0]["customer_id"],
        "delivery_date": iso(today),
        "quantity_delivered": over_finished_lot["quantity_produced"] + 100,
        "status": "DELIVERED"
    })

    ground_truth.append({
        "label_id": f"GT-{len(ground_truth)+1:05d}",
        "label_type": "ANOMALY_OVERDELIVERY",
        "entity_type": "FINISHED_LOT",
        "entity_id": over_finished_lot["finished_lot_id"],
        "expected_result": "DELIVERED_QUANTITY_EXCEEDS_PRODUCED",
        "rule": "Total delivered quantity must not exceed produced quantity."
    })

    # Recalculate shipment-lot totals after adding the exception.
    ship_fin_qty = defaultdict(int)

    for delivery in deliveries:
        key = (
            delivery["shipment_id"],
            delivery["finished_lot_id"]
        )
        ship_fin_qty[key] += delivery["quantity_delivered"]

    shipment_lots = []

    for idx, ((shipment_id, finished_id), qty) in enumerate(
        sorted(ship_fin_qty.items()), 1
    ):
        shipment_lots.append({
            "shipment_lot_id": f"SL-{idx:07d}",
            "shipment_id": shipment_id,
            "finished_lot_id": finished_id,
            "quantity_shipped": qty
        })

    # --------------------------------------------------
    # EXCEPTION 3 and 4: Add evaluation labels
    # --------------------------------------------------

    if missed_customer_id:
        ground_truth.append({
            "label_id": f"GT-{len(ground_truth)+1:05d}",
            "label_type": "ANOMALY_MISSED_CUSTOMER_NOTIFICATION",
            "entity_type": "CUSTOMER",
            "entity_id": missed_customer_id,
            "recall_case_id": missed_customer_case_id,
            "expected_result": "NOTIFICATION_INCOMPLETE",
            "rule": "Every downstream customer must receive a successful recall notification."
        })

    if unquarantined_fin_id:
        ground_truth.append({
            "label_id": f"GT-{len(ground_truth)+1:05d}",
            "label_type": "ANOMALY_RECALLED_STOCK_AVAILABLE",
            "entity_type": "FINISHED_LOT",
            "entity_id": unquarantined_fin_id,
            "expected_result": "SALE_BLOCK_REQUIRED",
            "rule": "A recalled finished lot must be quarantined and unavailable for sale."
        })

    # --------------------------------------------------
    # EXPORT DATA TABLES
    # --------------------------------------------------

    table_rows = {
        "suppliers": suppliers,
        "material_lots": raw_lots,
        "products": products,
        "boms": boms,
        "production_orders": production_orders,
        "material_consumptions": consumptions,
        "finished_lots": finished_lots,
        "shipments": shipments,
        "shipment_lots": shipment_lots,
        "customers": customers,
        "deliveries": deliveries,
        "recall_cases": recall_cases,
        "recall_actions": recall_actions,
        "state_events": state_events
    }

    for name, rows in table_rows.items():

        write_csv(
            out / f"{name}.csv",
            rows,
            TABLE_FIELDS[name]
        )

        with (out / f"{name}.json").open(
            "w", encoding="utf-8"
        ) as file:
            json.dump(rows, file, indent=2)

    # Ground truth is kept separate from operational data.
    with (out / "ground_truth.json").open(
        "w", encoding="utf-8"
    ) as file:
        json.dump(ground_truth, file, indent=2)

    ground_truth_fields = sorted({
        key
        for item in ground_truth
        for key in item
    })

    write_csv(
        out / "ground_truth.csv",
        ground_truth,
        ground_truth_fields
    )

    # --------------------------------------------------
    # VALIDATION
    # --------------------------------------------------

    id_sets = {
        "suppliers": {
            row["supplier_id"] for row in suppliers
        },
        "material_lots": {
            row["material_lot_id"] for row in raw_lots
        },
        "production_orders": {
            row["production_order_id"] for row in production_orders
        },
        "finished_lots": {
            row["finished_lot_id"] for row in finished_lots
        },
        "shipments": {
            row["shipment_id"] for row in shipments
        },
        "customers": {
            row["customer_id"] for row in customers
        }
    }

    missing_consumption = [
        row for row in consumptions
        if row["material_lot_id"] not in id_sets["material_lots"]
    ]

    missing_orders = [
        row for row in consumptions
        if row["production_order_id"] not in id_sets["production_orders"]
    ]

    delivered_by_finished = defaultdict(int)

    for delivery in deliveries:
        delivered_by_finished[
            delivery["finished_lot_id"]
        ] += delivery["quantity_delivered"]

    overdelivery = [
        lot for lot in finished_lots
        if delivered_by_finished[lot["finished_lot_id"]]
        > lot["quantity_produced"]
    ]


    duplicate_ids = {}

    for name, rows in table_rows.items():

        if name == "boms":
            values = [
                (row["bom_id"], row["material_id"])
                for row in rows
            ]
        else:
            key = TABLE_FIELDS[name][0]
            values = [
                row[key] for row in rows
            ]

        duplicate_ids[name] = (
            len(values) - len(set(values))
        )



    validation = {
        "seed": seed,
        "scale": scale,

        "counts": {
            name: len(rows)
            for name, rows in table_rows.items()
        },

        "ground_truth_labels": len(ground_truth),

        "checks": {
            "duplicate_primary_keys": duplicate_ids,
            "missing_consumption_material_lot_refs": len(
                missing_consumption
            ),
            "missing_consumption_production_order_refs": len(
                missing_orders
            ),
            "finished_lots_with_overdelivery": len(
                overdelivery
            ),
            "expected_planted_exceptions": {
                "missing_input_lot": 1,
                "overdelivery": 1,
                "missed_customer_notification": 1,
                "recalled_stock_available": 1
            }
        },

        "interpretation": (
            "Four deliberate exceptions are included. "
            "They must be detected by the application."
        ),

        "reproducibility": (
            "Generate twice with the same seed and compare "
            "the SHA-256 file checksums."
        )
    }

    with (out / "validation_summary.json").open(
        "w", encoding="utf-8"
    ) as file:
        json.dump(validation, file, indent=2)

    # --------------------------------------------------
    # GENERATE SQL EXPORT
    # --------------------------------------------------

    sql_lines = []

    for name, fields in TABLE_FIELDS.items():

        columns = ", ".join(
            f'"{field}" TEXT'
            for field in fields
        )

        sql_lines.append(
            f'CREATE TABLE IF NOT EXISTS "{name}" ({columns});'
        )

        for row in table_rows[name]:

            values = []

            for field in fields:

                value = row.get(field)

                if value is None or value == "":
                    values.append("NULL")
                else:
                    safe_value = str(value).replace("'", "''")
                    values.append(f"'{safe_value}'")

            field_names = ", ".join(
                f'"{field}"' for field in fields
            )

            sql_lines.append(
                f'INSERT INTO "{name}" ({field_names}) '
                f'VALUES ({", ".join(values)});'
            )

    (out / "seed.sql").write_text(
        "\n".join(sql_lines),
        encoding="utf-8"
    )

    # --------------------------------------------------
    # GENERATE SHA-256 MANIFEST
    # --------------------------------------------------

    manifest_files = []

    for file_path in sorted(out.iterdir()):

        if (
            file_path.is_file()
            and file_path.name != "source_manifest.json"
        ):

            file_hash = hashlib.sha256(
                file_path.read_bytes()
            ).hexdigest()

            manifest_files.append({
                "file": file_path.name,
                "bytes": file_path.stat().st_size,
                "sha256": file_hash
            })

    manifest = {
        "generator": "Synthetic supply chain data generator",
        "seed": seed,
        "scale": scale,
        "generated_on": iso(today),
        "files": manifest_files
    }

    with (out / "source_manifest.json").open(
        "w", encoding="utf-8"
    ) as file:
        json.dump(manifest, file, indent=2)

    print("\nDATASET GENERATION COMPLETED")
    print(json.dumps(validation, indent=2))


def main():

    parser = argparse.ArgumentParser(
        description="TraceRecall dataset generator"
    )

    parser.add_argument(
        "--scale",
        choices=["starter", "full"],
        default="starter"
    )

    parser.add_argument(
        "--seed",
        type=int,
        default=SEED
    )

    parser.add_argument(
        "--out",
        default="output"
    )

    args = parser.parse_args()

    generate(
        Path(args.out),
        args.scale,
        args.seed
    )


if __name__ == "__main__":
    main()
