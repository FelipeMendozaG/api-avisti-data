import json
from datetime import datetime
from io import BytesIO
from unittest.mock import Mock, patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase, override_settings
from openpyxl import Workbook
from rest_framework.test import APIClient

from apps.imports.exceptions import ImportValidationError
from apps.imports.parsers.csv_parser import CSVParser
from apps.imports.parsers.excel_parser import ExcelParser
from apps.imports.repositories.import_repository import ImportRepository
from apps.imports.services.import_service import ImportService


class ParserTests(SimpleTestCase):
    @override_settings(IMPORT_EXCEL_SHEET_NAME=None)
    def test_excel_valido_se_convierte_a_lista(self):
        workbook = Workbook()
        sheet = workbook.active
        sheet.append(["Registro", "Codigo", "Serie", "Descripcion", "Comienzo", "Vencimiento", "Cliente", "Usuario", "Fechareg", "EstadoArtAlqui", "GrupoKardex", "Cierre"])
        sheet.append([219082, "5100021518", "SCNU9423FM", "COMPUTADORA PORTATIL HP", datetime(2021, 1, 1), datetime(2021, 1, 1), "PROYECTOS DE INFRAE", "CFLORES", datetime(2010, 3, 18, 12, 6), "DEVOLUCION", "001-0028632", True])
        content = BytesIO()
        workbook.save(content)

        records = ExcelParser().parse(SimpleUploadedFile("datos.xlsx", content.getvalue()))

        self.assertEqual(records[0], {
            "Registro": 219082,
            "Co": "5100021518",
            "Serie": "SCNU9423FM",
            "Descripcion": "COMPUTADORA PORTATIL HP",
            "Comienzo": "01/01/2021 00:00",
            "Vencimiento": "01/01/2021 00:00",
            "Cliente": "PROYECTOS DE INFRAE",
            "Usuario": "CFLORES",
            "Fechareg": "18/03/2010 12:06",
            "EstadoArtA": "DEVOLUCION",
            "GrupoKarde": "001-0028632",
            "Cierre": "VERDADERO",
        })

    @override_settings(IMPORT_REQUIRED_COLUMNS=["documento", "nombre", "monto"])
    def test_csv_valido_respeta_utf8_y_saltos_de_linea(self):
        content = "documento,nombre,monto\n12345678,\"Ana López\",200.00\n".encode("utf-8")

        records = CSVParser().parse(SimpleUploadedFile("datos.csv", content))

        self.assertEqual(records, [{"documento": "12345678", "nombre": "Ana López", "monto": "200.00"}])

    def test_archivo_vacio_se_convierte_en_lista_vacia(self):
        self.assertEqual(CSVParser().parse(SimpleUploadedFile("datos.csv", b"")), [])

    def test_columnas_faltantes_se_aceptan(self):
        records = CSVParser().parse(SimpleUploadedFile("datos.csv", b"nombre\nJuan\n"))
        self.assertEqual(records, [{"nombre": "Juan"}])


class ServiceTests(SimpleTestCase):
    def test_service_envia_json_string_exactamente(self):
        repository = Mock()
        repository.execute.return_value = {"records_processed": 1}
        records = [{"documento": "123", "nombre": "José", "monto": 1.5}]

        ImportService(repository).process(records, "json")

        repository.execute.assert_called_once_with("json", json.dumps(records, ensure_ascii=False))

    def test_service_excel_envia_metadatos_y_json_string(self):
        repository = Mock()
        repository.execute_excel.return_value = {"load_id": 17, "status": "SUCCESS"}
        records = [{"documento": "123", "nombre": "José"}]

        result = ImportService(repository).process_excel(records, "AVISTI_IMPORTER", "datos.xlsx", "usuario")

        repository.execute_excel.assert_called_once_with(
            "AVISTI_IMPORTER",
            "datos.xlsx",
            "usuario",
            json.dumps(records, ensure_ascii=False),
        )
        self.assertEqual(result["procedure_result"]["load_id"], 17)


class RepositoryTests(SimpleTestCase):
    @patch("apps.imports.repositories.import_repository.connection")
    def test_repository_recupera_parametros_out_de_mysqlclient(self, connection_mock):
        cursor = connection_mock.cursor.return_value.__enter__.return_value
        cursor.callproc.return_value = ("AVISTI_IMPORTER", "datos.xlsx", "usuario", "[]", 0, "")
        cursor.description = None
        cursor.nextset.return_value = False
        cursor.fetchone.return_value = (17, "SUCCESS")

        result = ImportRepository().execute_excel("AVISTI_IMPORTER", "datos.xlsx", "usuario", "[]")

        cursor.callproc.assert_called_once_with(
            "sp_importar_excel",
            ["AVISTI_IMPORTER", "datos.xlsx", "usuario", "[]", 0, ""],
        )
        self.assertEqual(result["load_id"], 17)
        self.assertEqual(result["status"], "SUCCESS")


class EndpointTests(SimpleTestCase):
    def setUp(self):
        self.client = APIClient()

    @patch("apps.imports.api.views.ImportRepository")
    def test_json_acepta_objeto_y_responde_formato_consistente(self, repository_class):
        repository_class.return_value.execute.return_value = {"records_processed": 1}

        response = self.client.post(
            "/api/v1/import/json/",
            {"documento": "12345678", "nombre": "Juan", "monto": 150.50},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["success"])
        self.assertEqual(response.data["data"]["records_received"], 1)

    @patch("apps.imports.api.views.ImportRepository")
    def test_csv_usa_repository_mockeado(self, repository_class):
        repository_class.return_value.execute.return_value = {"records_processed": 1}

        response = self.client.post(
            "/api/v1/import/csv/",
            {"file": SimpleUploadedFile("datos.csv", b"documento,nombre\n123,Juan\n")},
            format="multipart",
        )

        self.assertEqual(response.status_code, 200)
        repository_class.return_value.execute.assert_called_once()
        sent_json = repository_class.return_value.execute.call_args.args[1]
        self.assertEqual(json.loads(sent_json), [{"documento": "123", "nombre": "Juan"}])

    @patch("apps.imports.api.views.ImportRepository")
    def test_excel_envia_parametros_del_procedimiento(self, repository_class):
        repository_class.return_value.execute_excel.return_value = {"load_id": 17, "status": "SUCCESS"}
        workbook = Workbook()
        workbook.active.append(["Registro", "Codigo", "Serie", "Descripcion", "Comienzo", "Vencimiento", "Cliente", "Usuario", "Fechareg", "EstadoArtAlqui", "GrupoKardex", "Cierre"])
        workbook.active.append([219082, "5100021518", "SCNU9423FM", "COMPUTADORA PORTATIL HP", datetime(2021, 1, 1), datetime(2021, 1, 1), "PROYECTOS DE INFRAE", "CFLORES", datetime(2010, 3, 18, 12, 6), "DEVOLUCION", "001-0028632", True])
        content = BytesIO()
        workbook.save(content)

        with override_settings(IMPORT_EXCEL_SHEET_NAME=None):
            response = self.client.post(
                "/api/v1/import/excel/",
                {
                    "file": SimpleUploadedFile("datos.xlsx", content.getvalue()),
                    "data_source": "AVISTI_IMPORTER",
                    "loaded_by": "usuario",
                },
                format="multipart",
            )

        self.assertEqual(response.status_code, 200)
        repository_class.return_value.execute_excel.assert_called_once()
        call_args = repository_class.return_value.execute_excel.call_args.args
        self.assertEqual(call_args[:3], ("AVISTI_IMPORTER", "datos.xlsx", "usuario"))
        sent_json = json.loads(call_args[3])
        self.assertEqual(sent_json[0]["Registro"], 219082)
        self.assertEqual(sent_json[0]["Co"], "5100021518")
        self.assertEqual(sent_json[0]["Comienzo"], "01/01/2021 00:00")
        self.assertEqual(sent_json[0]["Cierre"], "VERDADERO")

    def test_json_malformado_mantiene_respuesta_de_error(self):
        response = self.client.post(
            "/api/v1/import/json/",
            b'{"documento":',
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.data["success"])
        self.assertIn("errors", response.data)