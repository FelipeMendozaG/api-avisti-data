from django.test import SimpleTestCase
from rest_framework.test import APIClient
from unittest.mock import Mock, patch

from tests.support import ProtectedEndpointTestCase


ADMIN_ENDPOINTS = [
    "/api/v1/admin/entities",
    "/api/v1/admin/entities/1/verification",
    "/api/v1/admin/donation-requests",
    "/api/v1/admin/donation-requests/1",
    "/api/v1/admin/donation-requests/1/status",
    "/api/v1/admin/equipments/available-for-donation",
    "/api/v1/admin/donation-assignments",
    "/api/v1/admin/donation-assignments/1",
]


class AdminEndpointProtectionTests(SimpleTestCase):
    def setUp(self):
        self.client = APIClient()

    def test_todas_las_rutas_admin_requieren_bearer(self):
        for endpoint in ADMIN_ENDPOINTS:
            with self.subTest(endpoint=endpoint):
                response = self.client.get(endpoint)

                self.assertEqual(response.status_code, 401)
                self.assertFalse(response.data["success"])
                self.assertEqual(response.data["status"], "error")


class AvailableEquipmentFilterTests(ProtectedEndpointTestCase):
    @patch("apps.donations.api.views.Equipment")
    def test_filtra_por_nombre_codigo_o_serie_del_producto(self, equipment_model):
        ordered_queryset = Mock()
        equipment_model.objects.select_related.return_value.prefetch_related.return_value.filter.return_value.distinct.return_value.order_by.return_value = ordered_queryset
        ordered_queryset.filter.return_value = []

        response = self.client.get(
            "/api/v1/admin/equipments/available-for-donation",
            {"product_query": "adaptador"},
        )

        self.assertEqual(response.status_code, 200)
        filter_expression = ordered_queryset.filter.call_args.args[0]
        self.assertEqual(str(filter_expression), "(OR: ('product__name__icontains', 'adaptador'), ('product__product_code__icontains', 'adaptador'), ('serial_number__icontains', 'adaptador'))")