from django.db import models


class Supplier(models.Model):
    supplier_id = models.CharField(max_length=50, unique=True)
    supplier_name = models.CharField(max_length=200)
    country = models.CharField(max_length=100)
    risk_tier = models.CharField(max_length=50)
    status = models.CharField(max_length=50)

    def __str__(self):
        return self.supplier_name


class MaterialLot(models.Model):
    material_lot_id = models.CharField(max_length=100, unique=True)
    supplier = models.ForeignKey(
        Supplier, on_delete=models.CASCADE, related_name="material_lots"
    )
    status = models.CharField(max_length=50)

    def __str__(self):
        return self.material_lot_id


class ProductionOrder(models.Model):
    production_order_id = models.CharField(max_length=100, unique=True)
    product_id = models.CharField(max_length=100)
    bom_id = models.CharField(max_length=100, default="")
    planned_quantity = models.IntegerField(default=0)
    actual_quantity = models.IntegerField(default=0)
    planned_start = models.DateField(null=True, blank=True)
    actual_start = models.DateField(null=True, blank=True)
    actual_end = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=50)

    def __str__(self):
        return self.production_order_id

class FinishedLot(models.Model):
    finished_lot_id = models.CharField(max_length=100, unique=True)
    production_order = models.ForeignKey(
        ProductionOrder,
        on_delete=models.CASCADE,
        related_name="finished_lots"
    )
    product_id = models.CharField(max_length=100, default="")
    manufactured_date = models.DateField(null=True, blank=True)
    quantity_produced = models.IntegerField(default=0)
    quantity_available = models.IntegerField(default=0)
    status = models.CharField(max_length=50)

    def __str__(self):
        return self.finished_lot_id

class Shipment(models.Model):
    shipment_id = models.CharField(max_length=100, unique=True)
    carrier_name = models.CharField(max_length=100, default="")
    warehouse_id = models.CharField(max_length=100, default="")
    dispatch_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=50, default="PENDING")

    def __str__(self):
        return self.shipment_id

class ShipmentLot(models.Model):
    shipment_lot_id = models.CharField(max_length=100, unique=True)
    shipment = models.ForeignKey(
        Shipment,
        on_delete=models.CASCADE,
        related_name="shipment_lots"
    )
    finished_lot = models.ForeignKey(
        FinishedLot,
        on_delete=models.CASCADE,
        related_name="shipment_lots"
    )
    quantity_shipped = models.IntegerField(default=0)

    def __str__(self):
        return self.shipment_lot_id

class Delivery(models.Model):
    delivery_id = models.CharField(max_length=100, unique=True)

    shipment = models.ForeignKey(
        Shipment,
        on_delete=models.CASCADE,
        related_name="deliveries",
        null=True,
        blank=True
    )

    finished_lot = models.ForeignKey(
        FinishedLot,
        on_delete=models.CASCADE,
        related_name="deliveries",
        null=True,
        blank=True
    )

    customer_id = models.CharField(max_length=100, default="")
    delivery_date = models.DateField(null=True, blank=True)
    quantity = models.IntegerField(default=0)
    status = models.CharField(max_length=50, default="PENDING")

    def __str__(self):
        return self.delivery_id


class RecallCase(models.Model):
    recall_case_id = models.CharField(max_length=100, unique=True)
    trigger_entity_type = models.CharField(max_length=50)
    trigger_lot_id = models.CharField(max_length=100)
    reason = models.CharField(max_length=200)
    severity = models.CharField(max_length=50)
    opened_at = models.DateField()
    status = models.CharField(max_length=50, default="OPEN")

    scope_delivery_count = models.IntegerField(default=0)
    scope_quantity = models.IntegerField(default=0)

    # New recall tracking fields
    recovered_quantity = models.IntegerField(default=0)
    completed_at = models.DateField(null=True, blank=True)

    @property
    def pending_quantity(self):
        return max(0, self.scope_quantity - self.recovered_quantity)

    @property
    def completion_percentage(self):
        if self.scope_quantity <= 0:
            return 0

        percentage = (
            self.recovered_quantity / self.scope_quantity
        ) * 100

        return round(min(percentage, 100), 2)

    def __str__(self):
        return self.recall_case_id

class MaterialConsumption(models.Model):
    consumption_id = models.CharField(
        max_length=100,
        unique=True
    )

    production_order = models.ForeignKey(
        ProductionOrder,
        on_delete=models.CASCADE,
        related_name="material_consumptions"
    )

    material_lot = models.ForeignKey(
        MaterialLot,
        on_delete=models.CASCADE,
        related_name="consumptions"
    )

    material_id = models.CharField(max_length=100)
    quantity_consumed = models.IntegerField(default=0)
    consumed_at = models.DateField(null=True, blank=True)

    def __str__(self):
        return self.consumption_id
class RecallAction(models.Model):
    recall_action_id = models.CharField(max_length=50, unique=True)

    recall_case = models.ForeignKey(
        RecallCase,
        on_delete=models.CASCADE,
        related_name="actions"
    )

    action_type = models.CharField(max_length=50)
    target_type = models.CharField(max_length=50)
    target_id = models.CharField(max_length=100)

    action_date = models.DateField()
    status = models.CharField(max_length=30)

    quantity = models.IntegerField(default=0)
    notes = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.recall_action_id
