"""Pruebas de la paginación de los endpoints de listado.

Cubren `GET /api/v1/products/`, `GET /api/v1/equipments/` y `GET /api/v1/import/data-loads/`
(páginas, `page_size`, metadatos, combinación con filtros y errores 400/404).
No requieren MySQL: mockean el ORM igual que el resto de la suite.
"""

from unittest.mock import Mock, patch

from django.test import override_settings

from tests.support import ProtectedEndpointTestCase, build_data_load, build_equipment, build_product

PRODUCTS_URL = "/api/v1/products/"
EQUIPMENTS_URL = "/api/v1/equipments/"
DATA_LOADS_URL = "/api/v1/import/data-loads/"
PAGINATION_FIELDS = [
    "count",
    "page",
    "page_size",
    "total_pages",
    "next",
    "previous",
    "has_next",
    "has_previous",
]


class ProductPaginationTests(ProtectedEndpointTestCase):
    @patch("apps.catalog.api.views.Product")
    def test_primera_pagina_devuelve_metadatos_y_next(self, product_model):
        product_model.objects.all.return_value.order_by.return_value = [build_product(i) for i in range(1, 8)]

        response = self.client.get(PRODUCTS_URL, {"page": 1, "page_size": 3})
        payload = response.json()

        self.assertEqual(response.status_code, 200)
        self.assertTrue(payload["success"])
        self.assertEqual(sorted(payload["pagination"].keys()), sorted(PAGINATION_FIELDS))
        self.assertEqual([item["product_id"] for item in payload["data"]], [1, 2, 3])
        self.assertEqual(payload["pagination"]["count"], 7)
        self.assertEqual(payload["pagination"]["page"], 1)
        self.assertEqual(payload["pagination"]["page_size"], 3)
        self.assertEqual(payload["pagination"]["total_pages"], 3)
        self.assertTrue(payload["pagination"]["has_next"])
        self.assertFalse(payload["pagination"]["has_previous"])
        self.assertIsNone(payload["pagination"]["previous"])
        self.assertIn("page=2", payload["pagination"]["next"])
        self.assertIn("page_size=3", payload["pagination"]["next"])
        self.assertTrue(payload["pagination"]["next"].startswith("http://testserver/api/v1/products/"))

    @patch("apps.catalog.api.views.Product")
    def test_pagina_intermedia_devuelve_next_y_previous(self, product_model):
        product_model.objects.all.return_value.order_by.return_value = [build_product(i) for i in range(1, 8)]

        payload = self.client.get(PRODUCTS_URL, {"page": 2, "page_size": 3}).json()

        self.assertEqual([item["product_id"] for item in payload["data"]], [4, 5, 6])
        self.assertTrue(payload["pagination"]["has_next"])
        self.assertTrue(payload["pagination"]["has_previous"])
        self.assertIn("page=3", payload["pagination"]["next"])
        self.assertIn("page=1", payload["pagination"]["previous"])

    @patch("apps.catalog.api.views.Product")
    def test_ultima_pagina_devuelve_el_resto(self, product_model):
        product_model.objects.all.return_value.order_by.return_value = [build_product(i) for i in range(1, 8)]

        payload = self.client.get(PRODUCTS_URL, {"page": 3, "page_size": 3}).json()

        self.assertEqual([item["product_id"] for item in payload["data"]], [7])
        self.assertFalse(payload["pagination"]["has_next"])
        self.assertTrue(payload["pagination"]["has_previous"])
        self.assertIsNone(payload["pagination"]["next"])

    @patch("apps.catalog.api.views.Product")
    def test_paginacion_conserva_el_filtro_search(self, product_model):
        ordered_queryset = Mock()
        ordered_queryset.filter.return_value = [build_product(i) for i in range(1, 6)]
        product_model.objects.all.return_value.order_by.return_value = ordered_queryset

        payload = self.client.get(PRODUCTS_URL, {"search": "HP", "page": 2, "page_size": 2}).json()

        self.assertEqual([item["product_id"] for item in payload["data"]], [3, 4])
        self.assertEqual(payload["pagination"]["count"], 5)
        self.assertEqual(payload["pagination"]["total_pages"], 3)
        self.assertIn("search=HP", payload["pagination"]["next"])
        self.assertIn("search=HP", payload["pagination"]["previous"])
        ordered_queryset.filter.assert_called_once()

    @patch("apps.catalog.api.views.Product")
    @override_settings(PAGINATION_DEFAULT_PAGE_SIZE=2)
    def test_page_size_por_defecto_configurable(self, product_model):
        product_model.objects.all.return_value.order_by.return_value = [build_product(i) for i in range(1, 6)]

        payload = self.client.get(PRODUCTS_URL).json()

        self.assertEqual(len(payload["data"]), 2)
        self.assertEqual(payload["pagination"]["page_size"], 2)
        self.assertEqual(payload["pagination"]["total_pages"], 3)

    @patch("apps.catalog.api.views.Product")
    def test_listado_vacio_devuelve_pagina_vacia(self, product_model):
        product_model.objects.all.return_value.order_by.return_value = []

        payload = self.client.get(PRODUCTS_URL).json()

        self.assertEqual(payload["data"], [])
        self.assertEqual(payload["pagination"]["count"], 0)
        self.assertEqual(payload["pagination"]["total_pages"], 0)
        self.assertIsNone(payload["pagination"]["next"])
        self.assertIsNone(payload["pagination"]["previous"])

    @patch("apps.catalog.api.views.Product")
    def test_page_no_numerica_devuelve_400(self, product_model):
        product_model.objects.all.return_value.order_by.return_value = []

        response = self.client.get(PRODUCTS_URL, {"page": "abc"})

        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.json()["success"])
        self.assertEqual(response.json()["message"], "Parámetros de consulta inválidos")
        self.assertEqual(response.json()["errors"], {"page": "invalid"})

    @patch("apps.catalog.api.views.Product")
    def test_page_cero_devuelve_400(self, product_model):
        product_model.objects.all.return_value.order_by.return_value = []

        response = self.client.get(PRODUCTS_URL, {"page": 0})

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["errors"], {"page": "invalid"})

    @patch("apps.catalog.api.views.Product")
    def test_page_size_mayor_al_maximo_devuelve_400(self, product_model):
        product_model.objects.all.return_value.order_by.return_value = []

        response = self.client.get(PRODUCTS_URL, {"page_size": 101})

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["errors"], {"page_size": "max_100"})

    @patch("apps.catalog.api.views.Product")
    def test_pagina_fuera_de_rango_devuelve_404(self, product_model):
        product_model.objects.all.return_value.order_by.return_value = [build_product(i) for i in range(1, 4)]

        response = self.client.get(PRODUCTS_URL, {"page": 9, "page_size": 2})

        self.assertEqual(response.status_code, 404)
        payload = response.json()
        self.assertFalse(payload["success"])
        self.assertEqual(payload["message"], "Página fuera de rango")
        self.assertEqual(payload["errors"], {"page": "out_of_range"})


class EquipmentPaginationTests(ProtectedEndpointTestCase):
    @patch("apps.catalog.api.views.Equipment")
    def test_equipos_paginados_conservan_filtro_product_id(self, equipment_model):
        ordered_queryset = Mock()
        ordered_queryset.filter.return_value = [
            build_equipment(1, product=build_product(3)),
            build_equipment(2, product=build_product(3)),
            build_equipment(3, product=build_product(3)),
        ]
        equipment_model.objects.select_related.return_value.all.return_value.order_by.return_value = ordered_queryset

        payload = self.client.get(EQUIPMENTS_URL, {"product_id": "3", "page": 2, "page_size": 2}).json()

        self.assertEqual([item["equipment_id"] for item in payload["data"]], [3])
        self.assertEqual(payload["pagination"]["count"], 3)
        self.assertEqual(payload["pagination"]["total_pages"], 2)
        self.assertTrue(payload["pagination"]["has_previous"])
        self.assertIn("product_id=3", payload["pagination"]["previous"])
        ordered_queryset.filter.assert_called_once_with(product_id=3)

    @patch("apps.catalog.api.views.Equipment")
    def test_equipos_con_page_size_invalido_devuelve_400(self, equipment_model):
        equipment_model.objects.select_related.return_value.all.return_value.order_by.return_value = []

        response = self.client.get(EQUIPMENTS_URL, {"page_size": "muchos"})

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["errors"], {"page_size": "invalid"})


class DataLoadPaginationTests(ProtectedEndpointTestCase):
    @patch("apps.imports.api.list_views.DataLoad")
    def test_cargas_paginadas_devuelven_metadatos(self, data_load_model):
        data_load_model.objects.all.return_value.order_by.return_value = [
            build_data_load(3),
            build_data_load(2),
            build_data_load(1),
        ]

        payload = self.client.get(DATA_LOADS_URL, {"page": 1, "page_size": 1}).json()

        self.assertEqual([item["load_id"] for item in payload["data"]], [3])
        self.assertEqual(payload["pagination"]["count"], 3)
        self.assertEqual(payload["pagination"]["page_size"], 1)
        self.assertEqual(payload["pagination"]["total_pages"], 3)
        self.assertIn("page=2", payload["pagination"]["next"])
        data_load_model.objects.all.return_value.order_by.assert_called_once_with("-load_date")

    @patch("apps.imports.api.list_views.DataLoad")
    def test_cargas_con_pagina_fuera_de_rango_devuelve_404(self, data_load_model):
        data_load_model.objects.all.return_value.order_by.return_value = [build_data_load(1)]

        response = self.client.get(DATA_LOADS_URL, {"page": 4, "page_size": 1})

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["errors"], {"page": "out_of_range"})
