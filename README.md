# Supply Chain Traceability & Product Recall Simulator

A reproducible Python project that creates synthetic supplier-to-customer genealogy data, simulates recall execution, injects labelled exceptions, and exports CSV, JSON, and SQLite-compatible SQL seed data.

## Quick start

Requires Python 3.9+; no third-party packages are required.

```bash
python src/generate.py --scale starter --seed 20261022 --out output
```

Generate the requested full volume:

```bash
python src/generate.py --scale full --seed 20261022 --out output_full
```

Run twice into separate folders to compare `source_manifest.json` checksums:

```bash
python src/generate.py --scale starter --seed 20261022 --out run_a
python src/generate.py --scale starter --seed 20261022 --out run_b
```

The `sample_data/` directory contains the starter run, and `full_data/` contains the requested full-volume run. The generator is parameterized: starter and full runs use the same rules and fixed seed.

## Business workflow

1. Create suppliers, products, BOMs, and customers.
2. Create raw material lots with immutable supplier-linked IDs.
3. Create production orders and consumption bridge records linking each order to raw lots.
4. Create finished lots from production orders.
5. Create shipments, shipment-lot bridge records, and customer deliveries.
6. Plant synthetic contamination in selected source lots and create recall cases.
7. Traverse raw-lot → production order → finished lot → shipment/delivery genealogy.
8. Create explicit notification, quarantine, recovery-ready action records and state events.
9. Inject four labelled negative scenarios and report them without silently corrupting unrelated records.

## Main entities and cardinality

| Parent | Child / bridge | Cardinality |
|---|---|---|
| Supplier | MaterialLot | 1:N |
| Product | BOM | 1:N over revisions/components |
| Product | ProductionOrder | 1:N |
| BOM | ProductionOrder | 1:N |
| ProductionOrder | MaterialConsumption | 1:N |
| MaterialLot | MaterialConsumption | 1:N |
| ProductionOrder | FinishedLot | 1:N |
| Shipment | ShipmentLot | 1:N |
| FinishedLot | ShipmentLot | 1:N |
| Shipment | Delivery | 1:N |
| Customer | Delivery | 1:N |
| FinishedLot | Delivery | 1:N |
| RecallCase | RecallAction | 1:N |
| Entity | StateEvent | 1:N |

`MaterialConsumption` and `ShipmentLot` are bridge tables. `Delivery` links a shipment, finished lot, and customer. Effective dates are carried by BOM (`effective_from`, `effective_to`) and event/transaction dates. IDs are immutable. Lifecycle changes are represented by append-only `state_events.csv`, not overwritten history.

## ID conventions

- Supplier: `SUP-0001`
- Raw lot: `RAWLOT-SUP-0001-2026-000001`
- Production order: `WO-2026-000001`
- Finished lot: `FINLOT-000001`
- Shipment: `SHP-2026-000001`
- Recall: `REC-2026-000001`

## Four planted exceptions

1. Missing raw input lot reference in a consumption record.
2. Delivery quantity exceeds the corresponding finished-lot produced quantity.
3. One downstream customer notification is marked failed.
4. Recalled finished-lot inventory remains available for sale (quarantine action failed).

These are deliberately represented as labelled exceptions. `ground_truth.csv/json` is separate from operational input tables and must never be used as a model feature.

## Outputs

Each operational table is exported as both CSV and JSON. `seed.sql` contains SQLite-compatible `CREATE TABLE` and `INSERT` statements. `validation_summary.json` reports row counts, duplicate primary keys, foreign-key exceptions, and overdelivery detection. `source_manifest.json` records SHA-256 checksums. The source manifest documents that the data is fully synthetic and no external dataset was used.

## Important interpretation

The generator produces synthetic operational data for development, testing, and demonstration only. It is not a validated food, pharmaceutical, medical-device, or regulatory recall system. Before production use, add role-based access, audit controls, real carrier/customer integrations, jurisdiction-specific retention rules, and independent validation.
