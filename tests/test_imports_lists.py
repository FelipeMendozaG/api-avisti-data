from unittest.mock import MagicMock, Mock, patch

from django.test import SimpleTestCase

from apps.imports.models import DataLoad, ProcedureExecutionLog
from tests.support import ProtectedEndpointTestCase, build_data_load, build_log

DATA_LOADS_URL = "/api/v1/import/data-loads/"
LOGS_URL = "/api/v1/import/logs/"
DATA_LOAD_FIELDS = [
    "load_id",
    "data_source",
    "file_name",
    "load_date",
    "loaded_by",
    "processed_records",
    "load_status",
]
LOG_FIELDS = ["log_id", "load_id", "procedure_name", "log_level", "step_description", "message", "created_at"]


class DataLoadListViewTests(ProtectedEndpointTestCase):
    @patch("apps.imports.api.list_views.DataLoad")
    def test_data_loads_con_token_valido_devuelve_estructura_estandar(self, data_load_model):
        data_load_model.objects.all.return_value.order_by.return_value = [build_data_load(2), build_data_load(1)]

        response = self.client.get(DATA_LOADS_URL)

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["success"])
        self.assertEqual(response.data["message"], "Cargas de datos consultadas correctamente")
        self.assertEqual(len(response.data["data"]), 2)
        self.assertEqual(sorted(response.data["data"][0].keys()), sorted(DATA_LOAD_FIELDS))
        self.assertEqual(response.data["pagination"]["count"], 2)
        self.assertEqual(response.data["pagination"]["page"], 1)
        data_load_model.objects.all.return_value.order_by.assert_called_once_with("-load_date")

    @patch("apps.imports.api.list_views.DataLoad")
    def test_data_loads_devuelve_valores_serializados(self, data_load_model):
        data_load_model.objects.all.return_value.order_by.return_value = [build_data_load(5)]

        payload = self.client.get(DATA_LOADS_URL).json()

        self.assertEqual(payload["data"][0]["load_id"], 5)
        self.assertEqual(payload["data"][0]["data_source"], "AVISTI_IMPORTER")
        self.assertEqual(payload["data"][0]["file_name"], "carga-5.xlsx")
        self.assertEqual(payload["data"][0]["processed_records"], 10)
        self.assertEqual(payload["data"][0]["load_status"], "SUCCESS")


class ProcedureExecutionLogListViewTests(ProtectedEndpointTestCase):
    @patch("apps.imports.api.list_views.ProcedureExecutionLog")
    def test_logs_con_token_valido_devuelve_estructura_estandar(self, log_model):
        log_model.objects.all.return_value.order_by.return_value = [build_log(1)]

        response = self.client.get(LOGS_URL)

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["success"])
        self.assertEqual(response.data["message"], "Bitácora de ejecución consultada correctamente")
        self.assertEqual(sorted(response.data["data"][0].keys()), sorted(LOG_FIELDS))
        log_model.objects.all.return_value.order_by.assert_called_once_with("-created_at")

    @patch("apps.imports.api.list_views.ProcedureExecutionLog")
    def test_logs_devuelve_valores_serializados(self, log_model):
        log_model.objects.all.return_value.order_by.return_value = [build_log(9)]

        payload = self.client.get(LOGS_URL).json()

        self.assertEqual(payload["data"][0]["log_id"], 9)
        self.assertEqual(payload["data"][0]["procedure_name"], "sp_importar_excel")
        self.assertEqual(payload["data"][0]["log_level"], "INFO")
        self.assertEqual(payload["data"][0]["step_description"], "Paso 1")
        self.assertEqual(payload["data"][0]["message"], "Registro procesado")

    @patch("apps.imports.api.list_views.ProcedureExecutionLog")
    def test_logs_aplica_filtro_load_id(self, log_model):
        ordered_queryset = Mock()
        ordered_queryset.filter.return_value = [build_log(3, load_id=5)]
        log_model.objects.all.return_value.order_by.return_value = ordered_queryset

        response = self.client.get(LOGS_URL, {"load_id": "5"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["data"]), 1)
        ordered_queryset.filter.assert_called_once_with(load_id=5)

    @patch("apps.imports.api.list_views.ProcedureExecutionLog")
    def test_logs_sin_load_id_no_aplica_filtro(self, log_model):
        ordered_queryset = MagicMock()
        log_model.objects.all.return_value.order_by.return_value = ordered_queryset

        response = self.client.get(LOGS_URL)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["data"], [])
        ordered_queryset.filter.assert_not_called()

    @patch("apps.imports.api.list_views.ProcedureExecutionLog")
    def test_logs_con_load_id_invalido_devuelve_400(self, log_model):
        response = self.client.get(LOGS_URL, {"load_id": "abc"})

        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.data["success"])
        self.assertEqual(response.data["errors"], {"load_id": "invalid"})
        log_model.objects.all.assert_not_called()


class ImportsListModelTests(SimpleTestCase):
    def test_modelos_sin_managed_y_con_tablas_existentes(self):
        self.assertFalse(DataLoad._meta.managed)
        self.assertFalse(ProcedureExecutionLog._meta.managed)
        self.assertEqual(DataLoad._meta.db_table, "data_loads")
        self.assertEqual(ProcedureExecutionLog._meta.db_table, "procedure_execution_logs")