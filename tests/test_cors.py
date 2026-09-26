"""Pruebas de CORS: preflight y cabeceras en respuestas de éxito y de error.

No requieren MySQL: mockean el ORM igual que el resto de la suite.
"""

from unittest.mock import Mock, patch

from django.test import SimpleTestCase, override_settings
from rest_framework.test import APIClient

from tests.support import VALID_TOKEN, build_admin, build_product

PRODUCTS_URL = "/api/v1/products/"
EQUIPMENTS_URL = "/api/v1/equipments/"
DATA_LOADS_URL = "/api/v1/import/data-loads/"
LOGS_URL = "/api/v1/import/logs/"
PUBLIC_JSON_IMPORT_URL = "/api/v1/import/json/"
PUBLIC_CSV_IMPORT_URL = "/api/v1/import/csv/"
ANY_ORIGIN = "https://cualquier-app.ejemplo.com"
CORS_ALLOW_ORIGIN_VALUES = ("*", ANY_ORIGIN)


class PreflightTests(SimpleTestCase):
    """El preflight OPTIONS debe responder cabeceras CORS sin exigir token."""

    def setUp(self):
        self.client = APIClient()

    def test_preflight_de_endpoint_protegido_no_exige_token(self):
        response = self.client.options(
            PRODUCTS_URL,
            HTTP_ORIGIN=ANY_ORIGIN,
            HTTP_ACCESS_CONTROL_REQUEST_METHOD="GET",
            HTTP_ACCESS_CONTROL_REQUEST_HEADERS="authorization, content-type",
        )

        self.assertIn(response.status_code, (200, 204))
        self.assertIn(response["Access-Control-Allow-Origin"], CORS_ALLOW_ORIGIN_VALUES)
        self.assertIn("authorization", response["Access-Control-Allow-Headers"].lower())
        self.assertIn("content-type", response["Access-Control-Allow-Headers"].lower())
        self.assertIn("GET", response["Access-Control-Allow-Methods"])
        self.assertIn("OPTIONS", response["Access-Control-Allow-Methods"])

    def test_preflight_permite_post_multipart_en_importacion(self):
        response = self.client.options(
            PUBLIC_CSV_IMPORT_URL,
            HTTP_ORIGIN=ANY_ORIGIN,
            HTTP_ACCESS_CONTROL_REQUEST_METHOD="POST",
            HTTP_ACCESS_CONTROL_REQUEST_HEADERS="content-type",
        )

        self.assertIn(response.status_code, (200, 204))
        self.assertIn("POST", response["Access-Control-Allow-Methods"])
        self.assertIn(response["Access-Control-Allow-Origin"], CORS_ALLOW_ORIGIN_VALUES)

    def test_preflight_cachea_la_respuesta(self):
        response = self.client.options(
            LOGS_URL,
            HTTP_ORIGIN=ANY_ORIGIN,
            HTTP_ACCESS_CONTROL_REQUEST_METHOD="GET",
        )

        self.assertEqual(response["Access-Control-Max-Age"], "86400")

    def test_preflight_de_todos_los_listados_protegidos(self):
        for url in (PRODUCTS_URL, EQUIPMENTS_URL, DATA_LOADS_URL, LOGS_URL):
            with self.subTest(url=url):
                response = self.client.options(
                    url,
                    HTTP_ORIGIN=ANY_ORIGIN,
                    HTTP_ACCESS_CONTROL_REQUEST_METHOD="GET",
                )
                self.assertIn(response.status_code, (200, 204))
                self.assertIn(response["Access-Control-Allow-Origin"], CORS_ALLOW_ORIGIN_VALUES)


class CorsHeadersOnResponsesTests(SimpleTestCase):
    """Las respuestas con y sin token deben llevar cabeceras CORS legibles por el navegador."""

    def setUp(self):
        self.client = APIClient()

        patcher = patch("apps.authentication.authentication.AdminToken")
        self.admin_token_model = patcher.start()
        self.addCleanup(patcher.stop)

        admin_token = Mock(admin=build_admin())
        token_manager = self.admin_token_model.objects.select_related.return_value
        token_manager.filter.return_value.first.return_value = admin_token

    def test_listado_con_token_incluye_cabecera_cors(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {VALID_TOKEN}")

        with patch("apps.catalog.api.views.Product") as product_model:
            product_model.objects.all.return_value.order_by.return_value = [build_product(1)]
            response = self.client.get(PRODUCTS_URL, HTTP_ORIGIN=ANY_ORIGIN)

        self.assertEqual(response.status_code, 200)
        self.assertIn(response["Access-Control-Allow-Origin"], CORS_ALLOW_ORIGIN_VALUES)

    def test_respuesta_401_incluye_cabecera_cors(self):
        response = self.client.get(PRODUCTS_URL, HTTP_ORIGIN=ANY_ORIGIN)

        self.assertEqual(response.status_code, 401)
        self.assertIn(response["Access-Control-Allow-Origin"], CORS_ALLOW_ORIGIN_VALUES)
        self.assertFalse(response.json()["success"])

    @patch("apps.imports.api.views.ImportRepository")
    @patch("apps.imports.api.views.ImportService")
    def test_endpoint_publico_de_importacion_responde_con_cabecera_cors(self, import_service, import_repository):
        import_service.return_value.process.return_value = {"load_id": 1, "status": "SUCCESS"}

        response = self.client.post(
            PUBLIC_JSON_IMPORT_URL,
            {"documento": "12345678", "monto": 150.5},
            format="json",
            HTTP_ORIGIN=ANY_ORIGIN,
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["success"])
        self.assertIn(response["Access-Control-Allow-Origin"], CORS_ALLOW_ORIGIN_VALUES)
        import_repository.assert_called_once()

    def test_peticion_sin_origin_no_recibe_cabecera_cors(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {VALID_TOKEN}")

        with patch("apps.catalog.api.views.Product") as product_model:
            product_model.objects.all.return_value.order_by.return_value = []
            response = self.client.get(PRODUCTS_URL)

        self.assertEqual(response.status_code, 200)
        self.assertNotIn("Access-Control-Allow-Origin", response)


class RestrictedOriginsTests(SimpleTestCase):
    """Con CORS_ALLOW_ALL_ORIGINS=False solo los orígenes listados son aceptados."""

    def setUp(self):
        self.client = APIClient()

    @override_settings(
        CORS_ALLOW_ALL_ORIGINS=False,
        CORS_ALLOWED_ORIGINS=["https://permitida.ejemplo.com"],
    )
    def test_lista_blanca_de_origenes(self):
        allowed = self.client.options(
            PRODUCTS_URL,
            HTTP_ORIGIN="https://permitida.ejemplo.com",
            HTTP_ACCESS_CONTROL_REQUEST_METHOD="GET",
        )
        blocked = self.client.options(
            PRODUCTS_URL,
            HTTP_ORIGIN="https://otra-app.ejemplo.com",
            HTTP_ACCESS_CONTROL_REQUEST_METHOD="GET",
        )

        self.assertEqual(allowed["Access-Control-Allow-Origin"], "https://permitida.ejemplo.com")
        self.assertNotIn("Access-Control-Allow-Origin", blocked)
