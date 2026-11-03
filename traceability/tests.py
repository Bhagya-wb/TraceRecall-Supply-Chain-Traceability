from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import (
    Supplier,
    MaterialLot,
    ProductionOrder,
    FinishedLot,
    Delivery,
    RecallCase,
    RecallAction,
)


class TraceRecallModelTests(TestCase):

    def setUp(self):
        self.supplier = Supplier.objects.create(
            supplier_id="SUP-TEST-001",
            supplier_name="Test Supplier",
            country="India",
            risk_tier="LOW",
            status="ACTIVE",
        )

        self.material_lot = MaterialLot.objects.create(
            material_lot_id="RAW-TEST-001",
            supplier=self.supplier,
            status="AVAILABLE",
        )

        self.production_order = ProductionOrder.objects.create(
            production_order_id="WO-TEST-001",
            product_id="PROD-TEST-001",
            bom_id="BOM-TEST-001",
            planned_quantity=100,
            actual_quantity=100,
            status="COMPLETED",
        )

        self.finished_lot = FinishedLot.objects.create(
            finished_lot_id="FIN-TEST-001",
            production_order=self.production_order,
            product_id="PROD-TEST-001",
            quantity_produced=100,
            quantity_available=100,
            status="AVAILABLE",
        )

        self.recall = RecallCase.objects.create(
            recall_case_id="REC-TEST-001",
            trigger_entity_type="FINISHED_LOT",
            trigger_lot_id=self.finished_lot.finished_lot_id,
            reason="Test contamination",
            severity="CRITICAL",
            status="OPEN",
            scope_delivery_count=0,
            scope_quantity=100,
            opened_at=timezone.now(),
        )

    def test_supplier_and_material_lot_relationship(self):
        self.assertEqual(
            self.material_lot.supplier,
            self.supplier
        )

    def test_finished_lot_quantity(self):
        self.assertEqual(
            self.finished_lot.quantity_produced,
            100
        )

    def test_recall_case_creation(self):
        self.assertEqual(
            self.recall.status,
            "OPEN"
        )

    def test_recall_action_history(self):
        action = RecallAction.objects.create(
            recall_action_id="ACT-TEST-001",
            recall_case=self.recall,
            action_type="RECOVER",
            target_type="RECALL_CASE",
            target_id=self.recall.recall_case_id,
            action_date="2026-11-03",
            status="COMPLETED",
            quantity=10,
            notes="Automated test recovery",
        )

        self.assertEqual(action.quantity, 10)
        self.assertEqual(action.recall_case, self.recall)

    def test_dashboard_page_loads(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)

    def test_exception_report_page_loads(self):
        response = self.client.get("/exception-report/")
        self.assertEqual(response.status_code, 200)

    def test_recall_action_history_page_loads(self):
        response = self.client.get("/recall-action-history/")
        self.assertEqual(response.status_code, 200)