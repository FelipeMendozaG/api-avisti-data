"""Utilidades compartidas por las pruebas de autenticación, catálogo y listados.

Las pruebas mockean el ORM (no requieren conexión MySQL), igual que la suite
existente de importaciones.
"""

from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import Mock, patch

from django.contrib.auth.hashers import make_password
from django.test import SimpleTestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.authentication.models import Admin, AdminToken
from apps.catalog.models import Equipment, Product
from apps.imports.models import DataLoad, ProcedureExecutionLog

VALID_EMAIL = "admin@avisti.com"
VALID_PASSWORD = "Clave.Segura#2026"
VALID_TOKEN = "b" * 64
INVALID_TOKEN_MESSAGE = "Token inválido o expirado"
PROTECTED_ENDPOINTS = [
    "/api/v1/products/",
    "/api/v1/equipments/",
    "/api/v1/import/data-loads/",
    "/api/v1/import/logs/",
]


def build_admin(**overrides):
    values = {
        "id": 1,
        "name": "Admin Central",
        "email": VALID_EMAIL,
        "password": "pbkdf2_sha256$600000$hash-de-prueba",
    }
    values.update(overrides)
    return Admin(**values)


def build_admin_with_password(password=None):
    return build_admin(password=make_password(password or VALID_PASSWORD))


def build_admin_token(admin=None, **overrides):
    values = {
        "token_id": 1,
        "admin": admin or build_admin(),
        "token": VALID_TOKEN,
        "expires_at": timezone.now() + timedelta(hours=24),
    }
    values.update(overrides)
    return AdminToken(**values)


def build_product(product_id=1, **overrides):
    values = {
        "product_id": product_id,
        "product_code": f"P-{product_id:03d}",
        "name": f"Producto {product_id}",
        "url_image": f"https://cdn.avisti.com/products/{product_id}.png",
        "description": "Equipo de cómputo asignado",
        "category": "COMPUTO",
        "created_at": timezone.now(),
    }
    values.update(overrides)
    return Product(**values)


def build_equipment(equipment_id=1, product=None, **overrides):
    values = {
        "equipment_id": equipment_id,
        "product": product or build_product(),
        "load_id": 5,
        "serial_number": f"SN-{equipment_id:04d}",
        "acquisition_date": date(2024, 1, 15),
        "end_of_useful_life": date(2029, 1, 15),
        "current_market_value": Decimal("1500.50"),
        "life_cycle_status": "IN_USE",
        "created_at": timezone.now(),
        "updated_at": timezone.now(),
    }
    values.update(overrides)
    return Equipment(**values)


def build_data_load(load_id=1, **overrides):
    values = {
        "load_id": load_id,
        "data_source": "AVISTI_IMPORTER",
        "file_name": f"carga-{load_id}.xlsx",
        "load_date": timezone.now(),
        "loaded_by": "usuario",
        "processed_records": 10,
        "load_status": "SUCCESS",
    }
    values.update(overrides)
    return DataLoad(**values)


def build_log(log_id=1, **overrides):
    values = {
        "log_id": log_id,
        "load_id": 5,
        "procedure_name": "sp_importar_excel",
        "log_level": "INFO",
        "step_description": "Paso 1",
        "message": "Registro procesado",
        "created_at": timezone.now(),
    }
    values.update(overrides)
    return ProcedureExecutionLog(**values)


class ProtectedEndpointTestCase(SimpleTestCase):
    """Caso base para endpoints protegidos: simula un token Bearer vigente en la BD."""

    def setUp(self):
        self.client = APIClient()
        self.admin = build_admin()

        patcher = patch("apps.authentication.authentication.AdminToken")
        self.admin_token_model = patcher.start()
        self.addCleanup(patcher.stop)

        self.admin_token = Mock(admin=self.admin)
        token_manager = self.admin_token_model.objects.select_related.return_value
        token_manager.filter.return_value.first.return_value = self.admin_token

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {VALID_TOKEN}")