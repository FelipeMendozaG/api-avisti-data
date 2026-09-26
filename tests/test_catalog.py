from unittest.mock import MagicMock, Mock, patch

from django.test import SimpleTestCase

from apps.catalog.models import Equipment, Product
from tests.support import ProtectedEndpointTestCase, build_equipment, build_product

PRODUCTS_URL = "/api/v1/products/"
EQUIPMENTS_URL = "/api/v1/equipments/"
PRODUCT_FIELDS = ["product_id", "product_code", "name", "url_image", "description", "category", "created_at"]
EQUIPMENT_FIELDS = [
    "equipment_id",
    "product_id",
    "product_code",
    "load_id",
    "serial_number",
    "acquisition_date",
    "end_of_useful_life",
    "current_market_value",
    "life_cycle_status",
    "created_at",
    "updated_at",
]


class ProductListViewTests(ProtectedEndpointTestCase):
    @patch("apps.catalog.api.views.Product")
    def test_products_con_token_valido_devuelve_estructura_estandar(self, product_model):
        product_model.objects.all.return_value.order_by.return_value = [build_product(1), build_product(2)]

        response = self.client.get(PRODUCTS_URL)

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["success"])
        self.assertEqual(response.data["message"], "Productos consultados correctamente")
        self.assertEqual(sorted(response.data["data"][0].keys()), sorted(PRODUCT_FIELDS))
        self.assertEqual(len(response.data["data"]), 2)
        self.assertEqual(response.data["pagination"]["count"], 2)
        self.assertEqual(response.data["pagination"]["page"], 1)
        self.assertEqual(response.data["pagination"]["page_size"], 20)
        self.assertEqual(response.data["pagination"]["total_pages"], 1)
        product_model.objects.all.return_value.order_by.assert_called_once_with("product_id")

    @patch("apps.catalog.api.views.Product")
    def test_products_devuelve_valores_serializados(self, product_model):
        product_model.objects.all.return_value.order_by.return_value = [build_product(1)]

        response = self.client.get(PRODUCTS_URL)
        payload = response.json()

        self.assertEqual(payload["data"][0]["product_code"], "P-001")
        self.assertEqual(payload["data"][0]["name"], "Producto 1")
        self.assertEqual(payload["data"][0]["category"], "COMPUTO")
        self.assertEqual(payload["data"][0]["url_image"], "https://cdn.avisti.com/products/1.png")

    @patch("apps.catalog.api.views.Product")
    def test_products_aplica_filtro_search(self, product_model):
        ordered_queryset = Mock()
        ordered_queryset.filter.return_value = [build_product(2)]
        product_model.objects.all.return_value.order_by.return_value = ordered_queryset

        response = self.client.get(PRODUCTS_URL, {"search": "Producto 2"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["data"]), 1)
        ordered_queryset.filter.assert_called_once()

    @patch("apps.catalog.api.views.Product")
    def test_products_sin_search_no_aplica_filtro(self, product_model):
        ordered_queryset = MagicMock()
        ordered_queryset.count.return_value = 0
        ordered_queryset.__getitem__.return_value = []
        product_model.objects.all.return_value.order_by.return_value = ordered_queryset

        response = self.client.get(PRODUCTS_URL)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["data"], [])
        self.assertEqual(response.data["pagination"]["count"], 0)
        ordered_queryset.filter.assert_not_called()


class EquipmentListViewTests(ProtectedEndpointTestCase):
    @patch("apps.catalog.api.views.Equipment")
    def test_equipments_con_token_valido_devuelve_estructura_estandar(self, equipment_model):
        equipment_model.objects.select_related.return_value.all.return_value.order_by.return_value = [
            build_equipment(1),
            build_equipment(2, product=build_product(2)),
        ]

        response = self.client.get(EQUIPMENTS_URL)

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["success"])
        self.assertEqual(response.data["message"], "Equipos consultados correctamente")
        self.assertEqual(len(response.data["data"]), 2)
        self.assertEqual(sorted(response.data["data"][0].keys()), sorted(EQUIPMENT_FIELDS))
        self.assertEqual(response.data["pagination"]["count"], 2)
        self.assertFalse(response.data["pagination"]["has_next"])
        equipment_model.objects.select_related.assert_called_once_with("product")
        equipment_model.objects.select_related.return_value.all.return_value.order_by.assert_called_once_with(
            "equipment_id"
        )

    @patch("apps.catalog.api.views.Equipment")
    def test_equipments_devuelve_valores_serializados(self, equipment_model):
        equipment_model.objects.select_related.return_value.all.return_value.order_by.return_value = [
            build_equipment(7, product=build_product(3))
        ]

        response = self.client.get(EQUIPMENTS_URL)
        payload = response.json()

        self.assertEqual(payload["data"][0]["equipment_id"], 7)
        self.assertEqual(payload["data"][0]["product_id"], 3)
        self.assertEqual(payload["data"][0]["product_code"], "P-003")
        self.assertEqual(payload["data"][0]["serial_number"], "SN-0007")
        self.assertEqual(payload["data"][0]["life_cycle_status"], "IN_USE")
        self.assertEqual(float(payload["data"][0]["current_market_value"]), 1500.5)
        self.assertEqual(payload["data"][0]["acquisition_date"], "2024-01-15")

    @patch("apps.catalog.api.views.Equipment")
    def test_equipments_aplica_filtro_product_id(self, equipment_model):
        ordered_queryset = Mock()
        ordered_queryset.filter.return_value = [build_equipment(1)]
        equipment_model.objects.select_related.return_value.all.return_value.order_by.return_value = ordered_queryset

        response = self.client.get(EQUIPMENTS_URL, {"product_id": "3"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["data"]), 1)
        ordered_queryset.filter.assert_called_once_with(product_id=3)

    @patch("apps.catalog.api.views.Equipment")
    def test_equipments_con_product_id_invalido_devuelve_400(self, equipment_model):
        response = self.client.get(EQUIPMENTS_URL, {"product_id": "abc"})

        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.data["success"])
        self.assertEqual(response.data["errors"], {"product_id": "invalid"})
        equipment_model.objects.select_related.assert_not_called()


class CatalogModelTests(SimpleTestCase):
    def test_modelos_sin_managed_y_con_tablas_existentes(self):
        self.assertFalse(Product._meta.managed)
        self.assertFalse(Equipment._meta.managed)
        self.assertEqual(Product._meta.db_table, "products")
        self.assertEqual(Equipment._meta.db_table, "equipments")