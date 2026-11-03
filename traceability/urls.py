
from django.urls import path
from . import views

urlpatterns = [
    path("", views.dashboard, name="dashboard"),

    path("api/summary/", views.api_summary, name="api_summary"),
    path("api/suppliers/", views.api_suppliers, name="api_suppliers"),
    path("api/recalls/", views.api_recalls, name="api_recalls"),

    path("traceability/", views.traceability_search, name="traceability"),
    path("recall-simulation/", views.recall_simulation, name="recall_simulation"),

    path("create-recall-case/", views.create_recall_case, name="create_recall_case"),
    path("recall-recovery/", views.recall_recovery, name="recall_recovery"),
    path("recall-details/<str:recall_id>/", views.recall_details, name="recall_details"),

    path("export-recall-csv/", views.export_recall_csv, name="export_recall_csv"),
    path("exception-report/", views.exception_report, name="exception_report"),
    path("recall-action-history/", views.recall_action_history, name="recall_action_history"),
    path(
    "customer-notifications/",
    views.customer_notification,
    name="customer_notification",
),
    path(
    "product-quarantine/",
    views.product_quarantine,
    name="product_quarantine",
),
]
