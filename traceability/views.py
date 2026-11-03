
import csv
from io import StringIO
from django.db.models import Sum

from django.db.models import Sum, Count
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.utils import timezone
from django.views.decorators.http import require_POST

from .models import (
    Supplier,
    MaterialLot,
    ProductionOrder,
    FinishedLot,
    Shipment,
    ShipmentLot,
    Delivery,
    RecallCase,
    MaterialConsumption,
    RecallAction,
)

from .services import detect_exceptions


# --------------------------------------------------
# DASHBOARD
# --------------------------------------------------


def dashboard(request):
    # Supply Chain Statistics
    total_suppliers = Supplier.objects.count()
    total_material_lots = MaterialLot.objects.count()
    total_production_orders = ProductionOrder.objects.count()
    total_finished_lots = FinishedLot.objects.count()
    total_shipments = Shipment.objects.count()
    total_deliveries = Delivery.objects.count()

    # Recall Statistics
    total_recalls = RecallCase.objects.count()

    open_recalls = RecallCase.objects.filter(status="OPEN").count()
    in_progress_recalls = RecallCase.objects.filter(
        status="IN_PROGRESS"
    ).count()
    completed_recalls = RecallCase.objects.filter(
        status="COMPLETED"
    ).count()

    critical_recalls = RecallCase.objects.filter(
        severity="CRITICAL"
    ).count()

    high_recalls = RecallCase.objects.filter(
        severity="HIGH"
    ).count()

    # Recovery Statistics
    total_affected_quantity = RecallCase.objects.aggregate(
        total=Sum("scope_quantity")
    )["total"] or 0

    total_recovered_quantity = RecallCase.objects.aggregate(
        total=Sum("recovered_quantity")
    )["total"] or 0

    total_pending_quantity = max(
        total_affected_quantity - total_recovered_quantity, 0
    )

    overall_recovery_percentage = (
        round(
            (total_recovered_quantity / total_affected_quantity) * 100, 2
        )
        if total_affected_quantity else 0
    )

    # Recovery Action History
    recovery_actions = RecallAction.objects.filter(
        action_type="RECOVER"
    )

    total_recovery_actions = recovery_actions.count()

    completed_recovery_actions = recovery_actions.filter(
        status="COMPLETED"
    ).count()

    total_action_recovered_quantity = (
        recovery_actions.aggregate(total=Sum("quantity"))["total"] or 0
    )

    # Recall Status Chart Data
    recall_status_data = [
        {"label": "Open", "count": open_recalls},
        {"label": "In Progress", "count": in_progress_recalls},
        {"label": "Completed", "count": completed_recalls},
    ]

    # Recovery Chart Data
    recovery_data = [
        {
            "label": "Recovered",
            "quantity": total_recovered_quantity,
        },
        {
            "label": "Pending",
            "quantity": total_pending_quantity,
        },
    ]

    # Recent Recall Cases
    recent_recalls = RecallCase.objects.order_by("-opened_at")[:5]

    context = {
        "total_suppliers": total_suppliers,
        "total_material_lots": total_material_lots,
        "total_production_orders": total_production_orders,
        "total_finished_lots": total_finished_lots,
        "total_shipments": total_shipments,
        "total_deliveries": total_deliveries,

        "total_recalls": total_recalls,
        "open_recalls": open_recalls,
        "in_progress_recalls": in_progress_recalls,
        "completed_recalls": completed_recalls,
        "critical_recalls": critical_recalls,
        "high_recalls": high_recalls,

        "total_recovery_actions": total_recovery_actions,
        "completed_recovery_actions": completed_recovery_actions,
        "total_action_recovered_quantity": total_action_recovered_quantity,

        "total_affected_quantity": total_affected_quantity,
        "total_recovered_quantity": total_recovered_quantity,
        "total_pending_quantity": total_pending_quantity,
        "overall_recovery_percentage": overall_recovery_percentage,

        "recall_status_data": recall_status_data,
        "recovery_data": recovery_data,
        "recent_recalls": recent_recalls,
    }

    return render(
        request,
        "traceability/dashboard.html",
        context
    )


# --------------------------------------------------
# API ENDPOINTS
# --------------------------------------------------

def api_summary(request):
    data = {
        "suppliers": Supplier.objects.count(),
        "material_lots": MaterialLot.objects.count(),
        "production_orders": ProductionOrder.objects.count(),
        "finished_lots": FinishedLot.objects.count(),
        "shipments": Shipment.objects.count(),
        "deliveries": Delivery.objects.count(),
        "recalls": RecallCase.objects.count(),
    }

    return JsonResponse(data)


def api_suppliers(request):
    suppliers = Supplier.objects.all().values(
        "supplier_id",
        "supplier_name",
        "country",
        "risk_tier",
        "status",
    )

    return JsonResponse(list(suppliers), safe=False)


def api_recalls(request):
    recalls = RecallCase.objects.all().values(
        "recall_case_id",
        "trigger_entity_type",
        "trigger_lot_id",
        "reason",
        "severity",
        "status",
        "scope_quantity",
        "recovered_quantity",
    )

    return JsonResponse(list(recalls), safe=False)


# --------------------------------------------------
# TRACEABILITY SEARCH
# --------------------------------------------------

def traceability_search(request):
    query = request.GET.get("q", "").strip()

    suppliers = Supplier.objects.none()
    material_lots = MaterialLot.objects.none()
    production_orders = ProductionOrder.objects.none()
    finished_lots = FinishedLot.objects.none()
    shipments = Shipment.objects.none()
    deliveries = Delivery.objects.none()

    if query:
        suppliers = Supplier.objects.filter(
            supplier_id__icontains=query
        ) | Supplier.objects.filter(
            supplier_name__icontains=query
        )

        material_lots = MaterialLot.objects.filter(
            material_lot_id__icontains=query
        )

        production_orders = ProductionOrder.objects.filter(
            production_order_id__icontains=query
        )

        finished_lots = FinishedLot.objects.filter(
            finished_lot_id__icontains=query
        ) | FinishedLot.objects.filter(
            product_id__icontains=query
        )

        shipments = Shipment.objects.filter(
            shipment_id__icontains=query
        )

        deliveries = Delivery.objects.filter(
            delivery_id__icontains=query
        ) | Delivery.objects.filter(
            customer_id__icontains=query
        )

    context = {
        "query": query,
        "suppliers": suppliers,
        "material_lots": material_lots,
        "production_orders": production_orders,
        "finished_lots": finished_lots,
        "shipments": shipments,
        "deliveries": deliveries,
    }

    return render(request, "traceability/traceability.html", context)


# --------------------------------------------------
# RECALL SIMULATION
# --------------------------------------------------

def recall_simulation(request):
    material_lots = MaterialLot.objects.all().order_by("material_lot_id")

    context = {
        "material_lots": material_lots,
    }

    return render(request, "traceability/recall_simulation.html", context)


# --------------------------------------------------
# CREATE RECALL CASE
# --------------------------------------------------

@require_POST
def create_recall_case(request):
    trigger_lot_id = request.POST.get("trigger_lot_id", "").strip()
    reason = request.POST.get("reason", "").strip()

    if not trigger_lot_id or not reason:
        return HttpResponse(
            "Please provide a material lot ID and recall reason.",
            status=400,
        )

    material_lot = get_object_or_404(
        MaterialLot,
        material_lot_id=trigger_lot_id,
    )

    existing_recall = RecallCase.objects.filter(
        trigger_lot_id=trigger_lot_id,
        status__in=["OPEN", "IN_PROGRESS"],
    ).first()

    if existing_recall:
        return redirect(
            "recall_details",
            recall_id=existing_recall.recall_case_id,
        )

    affected_orders = ProductionOrder.objects.filter(
        material_consumptions__material_lot=material_lot
    ).distinct()

    affected_finished_lots = FinishedLot.objects.filter(
        production_order__in=affected_orders
    )

    affected_deliveries = Delivery.objects.filter(
        finished_lot__in=affected_finished_lots
    )

    scope_delivery_count = affected_deliveries.count()

    scope_quantity = affected_deliveries.aggregate(
        total=Sum("quantity")
    )["total"] or 0

    recall_number = RecallCase.objects.count() + 1
    recall_id = f"REC-MANUAL-{timezone.now().strftime('%Y%m%d%H%M%S')}"

    recall = RecallCase.objects.create(
        recall_case_id=recall_id,
        trigger_entity_type="RAW",
        trigger_lot_id=trigger_lot_id,
        reason=reason,
        severity="CRITICAL",
        opened_at=timezone.now(),
        status="OPEN",
        scope_delivery_count=scope_delivery_count,
        scope_quantity=scope_quantity,
        recovered_quantity=0,
    )

    return redirect(
        "recall_details",
        recall_id=recall.recall_case_id,
    )


# --------------------------------------------------
# RECALL RECOVERY
# --------------------------------------------------

def recall_recovery(request):
    # GET request: Open the Recall Recovery page
    if request.method == "GET":
        recalls = RecallCase.objects.all().order_by("-opened_at")
        return render(
            request,
            "traceability/recall_recovery.html",
            {
                "recalls": recalls,
                "recall_cases": recalls,
            },
        )

    # POST request: Record recovered quantity
    if request.method == "POST":
        recall_id = request.POST.get("recall_case_id")
        quantity = request.POST.get("quantity")

        recall = get_object_or_404(
            RecallCase,
            recall_case_id=recall_id,
        )

        try:
            quantity = int(quantity)
        except (TypeError, ValueError):
            return HttpResponse(
                "Please enter a valid quantity.",
                status=400,
            )

        if quantity <= 0:
            return HttpResponse(
                "Quantity must be greater than zero.",
                status=400,
            )

        pending = max(
            recall.scope_quantity - recall.recovered_quantity,
            0,
        )

        if quantity > pending:
            return HttpResponse(
                f"Quantity cannot exceed the pending quantity ({pending}).",
                status=400,
            )

        recall.recovered_quantity += quantity

        if recall.recovered_quantity >= recall.scope_quantity:
            recall.status = "COMPLETED"
            recall.completed_at = timezone.now()
        else:
            recall.status = "IN_PROGRESS"

        recall.save()

        RecallAction.objects.create(
            recall_action_id=(
                f"ACT-RECOVER-{timezone.now().strftime('%Y%m%d%H%M%S%f')}"
            ),
            recall_case=recall,
            action_type="RECOVER",
            target_type="RECALL",
            target_id=recall.recall_case_id,
            action_date=timezone.localdate(),
            status="COMPLETED",
            quantity=quantity,
            notes="Recovery quantity recorded through the application.",
        )

        return redirect(
            "recall_details",
            recall_id=recall.recall_case_id,
        )

    return HttpResponse("Method not allowed.", status=405)

# --------------------------------------------------
# RECALL DETAILS
# --------------------------------------------------

def recall_details(request, recall_id):
    recall = get_object_or_404(
        RecallCase,
        recall_case_id=recall_id,
    )

    if recall.trigger_entity_type == "RAW":
        material_lot = MaterialLot.objects.filter(
            material_lot_id=recall.trigger_lot_id
        ).first()

        production_orders = ProductionOrder.objects.filter(
            material_consumptions__material_lot=material_lot
        ).distinct() if material_lot else ProductionOrder.objects.none()

        finished_lots = FinishedLot.objects.filter(
            production_order__in=production_orders
        )

    elif recall.trigger_entity_type == "FINISHED_LOT":
        production_orders = ProductionOrder.objects.none()
        finished_lots = FinishedLot.objects.filter(
            finished_lot_id=recall.trigger_lot_id
        )

    else:
        production_orders = ProductionOrder.objects.none()
        finished_lots = FinishedLot.objects.none()

    deliveries = Delivery.objects.filter(
        finished_lot__in=finished_lots
    ).select_related("finished_lot")

    actions = RecallAction.objects.filter(
        recall_case=recall
    ).order_by("-action_date", "-id")

    context = {
        "recall": recall,
        "production_orders": production_orders,
        "finished_lots": finished_lots,
        "deliveries": deliveries,
        "actions": actions,
    }

    return render(request, "traceability/recall_details.html", context)


# --------------------------------------------------
# EXPORT RECALL DATA TO CSV
# --------------------------------------------------

def export_recall_csv(request):
    recalls = RecallCase.objects.all().order_by("recall_case_id")

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = (
        'attachment; filename="recall_report.csv"'
    )

    writer = csv.writer(response)

    writer.writerow([
        "Recall ID",
        "Trigger Type",
        "Trigger Lot ID",
        "Reason",
        "Severity",
        "Status",
        "Scope Quantity",
        "Recovered Quantity",
        "Opened At",
    ])

    for recall in recalls:
        writer.writerow([
            recall.recall_case_id,
            recall.trigger_entity_type,
            recall.trigger_lot_id,
            recall.reason,
            recall.severity,
            recall.status,
            recall.scope_quantity,
            recall.recovered_quantity,
            recall.opened_at,
        ])

    return response


# --------------------------------------------------
# EXCEPTION REPORT
# --------------------------------------------------

def exception_report(request):
    exceptions = detect_exceptions()

    return render(
        request,
        "exception_report.html",
        {"exceptions": exceptions},
    )


# --------------------------------------------------
# RECALL ACTION HISTORY
# --------------------------------------------------

def recall_action_history(request):
    actions = RecallAction.objects.select_related(
        "recall_case"
    ).all().order_by("-action_date", "-id")

    return render(
        request,
        "traceability/recall_action_history.html",
        {"actions": actions},
    )


# --------------------------------------------------
# CUSTOMER NOTIFICATION HELPERS
# --------------------------------------------------

def get_affected_deliveries(recall):
    if recall.trigger_entity_type == "RAW":
        return Delivery.objects.filter(
            finished_lot__production_order__material_consumptions__material_lot__material_lot_id=recall.trigger_lot_id
        ).select_related("finished_lot").distinct()

    if recall.trigger_entity_type == "FINISHED_LOT":
        return Delivery.objects.filter(
            finished_lot__finished_lot_id=recall.trigger_lot_id
        ).select_related("finished_lot").distinct()

    return Delivery.objects.none()


# --------------------------------------------------
# CUSTOMER NOTIFICATION MANAGEMENT
# --------------------------------------------------

def customer_notification(request):
    recalls = RecallCase.objects.all().order_by("-opened_at")

    selected_recall_id = request.GET.get("recall_id") or request.POST.get("recall_id")

    selected_recall = None
    customers = []
    error_message = ""
    success_message = ""

    if selected_recall_id:
        selected_recall = get_object_or_404(
            RecallCase,
            recall_case_id=selected_recall_id,
        )

    if request.method == "POST":
        customer_id = request.POST.get("customer_id", "").strip()

        if not selected_recall:
            error_message = "Please select a recall case."

        elif not customer_id:
            error_message = "Customer ID is required."

        else:
            affected_customer_ids = set(
                get_affected_deliveries(selected_recall)
                .values_list("customer_id", flat=True)
                .distinct()
            )

            if customer_id not in affected_customer_ids:
                error_message = "This customer is not affected by the selected recall."

            else:
                already_sent = RecallAction.objects.filter(
                    recall_case=selected_recall,
                    action_type="NOTIFY_CUSTOMER",
                    target_type="CUSTOMER",
                    target_id=customer_id,
                    status="SENT",
                ).exists()

                if already_sent:
                    error_message = "This customer has already been marked as notified."

                else:
                    RecallAction.objects.create(
                        recall_action_id=(
                            f"ACT-NOTIFY-{timezone.now().strftime('%Y%m%d%H%M%S%f')}"
                        ),
                        recall_case=selected_recall,
                        action_type="NOTIFY_CUSTOMER",
                        target_type="CUSTOMER",
                        target_id=customer_id,
                        action_date=timezone.localdate(),
                        status="SENT",
                        quantity=0,
                        notes="Customer notification simulated and recorded in TraceRecall.",
                    )

                    success_message = (
                        f"Notification recorded successfully for {customer_id}."
                    )

    if selected_recall:
        affected_customer_ids = (
            get_affected_deliveries(selected_recall)
            .values_list("customer_id", flat=True)
            .distinct()
        )

        for customer_id in affected_customer_ids:
            latest_action = RecallAction.objects.filter(
                recall_case=selected_recall,
                action_type="NOTIFY_CUSTOMER",
                target_type="CUSTOMER",
                target_id=customer_id,
            ).order_by("-action_date", "-id").first()

            customers.append({
                "customer_id": customer_id,
                "status": latest_action.status if latest_action else "PENDING",
            })

    context = {
        "recalls": recalls,
        "selected_recall": selected_recall,
        "customers": customers,
        "error_message": error_message,
        "success_message": success_message,
    }

    return render(
        request,
        "traceability/customer_notifications.html",
        context,
    )
def product_quarantine(request):
    recalls = RecallCase.objects.all().order_by("-opened_at")
    selected_recall = None
    affected_lots = []

    recall_id = request.GET.get("recall_id") or request.POST.get("recall_id")

    if recall_id:
        selected_recall = get_object_or_404(
            RecallCase, recall_case_id=recall_id
        )

        if selected_recall.trigger_entity_type == "FINISHED_LOT":
            affected_lots = FinishedLot.objects.filter(
                finished_lot_id=selected_recall.trigger_lot_id
            )

        elif selected_recall.trigger_entity_type == "RAW":
            affected_lots = FinishedLot.objects.filter(
                production_order__material_consumptions__material_lot__material_lot_id=
                selected_recall.trigger_lot_id
            ).distinct()

        if request.method == "POST":
            quarantined_count = 0

            for lot in affected_lots:
                if lot.quantity_available > 0 and lot.status != "QUARANTINED":
                    lot.status = "QUARANTINED"
                    lot.save(update_fields=["status"])

                    RecallAction.objects.create(
                        recall_action_id=(
                            f"QUAR-{selected_recall.recall_case_id}-"
                            f"{lot.finished_lot_id}"
                        ),
                        recall_case=selected_recall,
                        action_type="QUARANTINE",
                        target_type="FINISHED_LOT",
                        target_id=lot.finished_lot_id,
                        action_date=timezone.localdate(),
                        status="COMPLETED",
                        quantity=lot.quantity_available,
                        notes="Affected stock quarantined in the system."
                    )
                    quarantined_count += 1

            return redirect(
                f"{request.path}?recall_id={selected_recall.recall_case_id}"
            )

    return render(
        request,
        "traceability/product_quarantine.html",
        {
            "recalls": recalls,
            "selected_recall": selected_recall,
            "affected_lots": affected_lots,
        },
    )
