from django.urls import path

from apps.imports.api.list_views import DataLoadListView, ProcedureExecutionLogListView
from apps.imports.api.views import CSVImportView, ExcelImportView, JSONImportView

urlpatterns = [
    path("excel/", ExcelImportView.as_view(), name="import-excel"),
    path("csv/", CSVImportView.as_view(), name="import-csv"),
    path("json/", JSONImportView.as_view(), name="import-json"),
    path("data-loads/", DataLoadListView.as_view(), name="import-data-loads"),
    path("logs/", ProcedureExecutionLogListView.as_view(), name="import-logs"),
]