import re
from datetime import timedelta
from io import StringIO
from unittest.mock import Mock, patch

from django.contrib.auth.hashers import check_password
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import SimpleTestCase
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from rest_framework.test import APIClient

from apps.authentication.models import Admin, AdminToken
from tests.support import (
    INVALID_TOKEN_MESSAGE,
    PROTECTED_ENDPOINTS,
    VALID_EMAIL,
    VALID_PASSWORD,
    VALID_TOKEN,
    ProtectedEndpointTestCase,
    build_admin_with_password,
)

LOGIN_URL = "/api/v1/auth/login/"
LOGOUT_URL = "/api/v1/auth/logout/"


class LoginSuccessTests(SimpleTestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = build_admin_with_password()
        self.issued_token = Mock()
        self.issued_token.token = "a" * 64
        self.issued_token.expires_at = timezone.now() + timedelta(hours=24)

    def _login(self, payload):
        with patch("apps.authentication.api.views.Admin") as admin_model, patch(
            "apps.authentication.api.views.AdminToken"
        ) as token_model:
            admin_model.objects.filter.return_value.first.return_value = self.admin
            token_model.objects.create.return_value = self.issued_token
            response = self.client.post(LOGIN_URL, payload, format="json")
            return response, admin_model, token_model

    def test_login_con_credenciales_validas_devuelve_token(self):
        response, admin_model, token_model = self._login({"email": VALID_EMAIL, "password": VALID_PASSWORD})

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["success"])
        self.assertEqual(response.data["message"], "Autenticación exitosa")
        self.assertEqual(response.data["data"]["token"], self.issued_token.token)
        payload = response.json()
        self.assertEqual(payload["data"]["token"], self.issued_token.token)
        self.assertEqual(parse_datetime(payload["data"]["expires_at"]), self.issued_token.expires_at)
        admin_model.objects.filter.assert_called_once_with(email=VALID_EMAIL)
        token_model.objects.create.assert_called_once()

    def test_login_genera_token_hex_de_64_caracteres_vigente_24_horas(self):
        before = timezone.now() + timedelta(hours=23, minutes=59)
        after = timezone.now() + timedelta(hours=24, minutes=1)

        _, _, token_model = self._login({"email": VALID_EMAIL, "password": VALID_PASSWORD})

        create_kwargs = token_model.objects.create.call_args.kwargs
        self.assertEqual(create_kwargs["admin"], self.admin)
        self.assertEqual(len(create_kwargs["token"]), 64)
        self.assertRegex(create_kwargs["token"], re.compile(r"^[0-9a-f]{64}$"))
        self.assertTrue(before < create_kwargs["expires_at"] < after)

    def test_login_no_expone_el_password_ni_el_hash(self):
        response, _, _ = self._login({"email": VALID_EMAIL, "password": VALID_PASSWORD})

        self.assertNotIn("password", response.data["data"])
        self.assertNotIn("password", response.data)


class LoginFailureTests(SimpleTestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = build_admin_with_password()

    def _login(self, payload, admin=None):
        with patch("apps.authentication.api.views.Admin") as admin_model, patch(
            "apps.authentication.api.views.AdminToken"
        ) as token_model:
            admin_model.objects.filter.return_value.first.return_value = admin
            response = self.client.post(LOGIN_URL, payload, format="json")
            return response, token_model

    def test_login_con_password_incorrecta_devuelve_401(self):
        response, token_model = self._login({"email": VALID_EMAIL, "password": "clave-incorrecta"}, admin=self.admin)

        self.assertEqual(response.status_code, 401)
        self.assertFalse(response.data["success"])
        self.assertEqual(response.data["message"], "Credenciales inválidas")
        self.assertIn("errors", response.data)
        token_model.objects.create.assert_not_called()

    def test_login_con_email_inexistente_devuelve_401(self):
        response, token_model = self._login({"email": "nadie@avisti.com", "password": VALID_PASSWORD}, admin=None)

        self.assertEqual(response.status_code, 401)
        self.assertFalse(response.data["success"])
        self.assertIn("errors", response.data)
        token_model.objects.create.assert_not_called()

    def test_login_sin_password_devuelve_400(self):
        response, token_model = self._login({"email": VALID_EMAIL}, admin=self.admin)

        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.data["success"])
        self.assertIn("errors", response.data)
        token_model.objects.create.assert_not_called()

    def test_login_con_email_invalido_devuelve_400(self):
        response, _ = self._login({"email": "correo-invalido", "password": VALID_PASSWORD}, admin=self.admin)

        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.data["success"])


class LogoutTests(ProtectedEndpointTestCase):
    def test_logout_elimina_el_token_actual(self):
        response = self.client.post(LOGOUT_URL)

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["success"])
        self.assertEqual(response.data["message"], "Sesión finalizada correctamente")
        self.admin_token.delete.assert_called_once()

    def test_logout_sin_token_devuelve_401(self):
        self.client.credentials()

        response = self.client.post(LOGOUT_URL)

        self.assertEqual(response.status_code, 401)
        self.assertFalse(response.data["success"])

    def test_logout_con_token_inexistente_o_expirado_devuelve_401(self):
        with patch("apps.authentication.authentication.AdminToken") as token_model:
            token_model.objects.select_related.return_value.filter.return_value.first.return_value = None

            response = self.client.post(LOGOUT_URL)

        self.assertEqual(response.status_code, 401)
        self.assertFalse(response.data["success"])
        self.assertEqual(response.data["message"], INVALID_TOKEN_MESSAGE)


class ProtectedEndpointAuthorizationTests(SimpleTestCase):
    def setUp(self):
        self.client = APIClient()

    def test_endpoints_protegidos_sin_header_devuelven_401(self):
        for endpoint in PROTECTED_ENDPOINTS:
            with self.subTest(endpoint=endpoint):
                response = self.client.get(endpoint)

                self.assertEqual(response.status_code, 401)
                self.assertFalse(response.data["success"])
                self.assertIn("message", response.data)
                self.assertIn("errors", response.data)

    def test_endpoints_protegidos_con_esquema_incorrecto_devuelven_401(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {VALID_TOKEN}")

        for endpoint in PROTECTED_ENDPOINTS:
            with self.subTest(endpoint=endpoint):
                response = self.client.get(endpoint)

                self.assertEqual(response.status_code, 401)
                self.assertFalse(response.data["success"])

    def test_endpoints_protegidos_con_header_malformado_devuelven_401(self):
        self.client.credentials(HTTP_AUTHORIZATION=VALID_TOKEN)

        for endpoint in PROTECTED_ENDPOINTS:
            with self.subTest(endpoint=endpoint):
                response = self.client.get(endpoint)

                self.assertEqual(response.status_code, 401)
                self.assertFalse(response.data["success"])

    def test_token_inexistente_o_expirado_devuelve_401(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {VALID_TOKEN}")

        with patch("apps.authentication.authentication.AdminToken") as token_model:
            token_model.objects.select_related.return_value.filter.return_value.first.return_value = None

            response = self.client.get(PROTECTED_ENDPOINTS[0])

        self.assertEqual(response.status_code, 401)
        self.assertFalse(response.data["success"])
        self.assertEqual(response.data["message"], INVALID_TOKEN_MESSAGE)

    def test_autenticacion_busca_token_vigente_con_select_related(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {VALID_TOKEN}")

        with patch("apps.authentication.authentication.AdminToken") as token_model:
            token_model.objects.select_related.return_value.filter.return_value.first.return_value = None

            self.client.get(PROTECTED_ENDPOINTS[0])

        token_model.objects.select_related.assert_called_once_with("admin")
        filter_kwargs = token_model.objects.select_related.return_value.filter.call_args.kwargs
        self.assertEqual(filter_kwargs["token"], VALID_TOKEN)
        self.assertIn("expires_at__gt", filter_kwargs)


class AdminModelTests(SimpleTestCase):
    def test_modelos_sin_managed_y_con_tablas_existentes(self):
        self.assertFalse(Admin._meta.managed)
        self.assertFalse(AdminToken._meta.managed)
        self.assertEqual(Admin._meta.db_table, "admins")
        self.assertEqual(AdminToken._meta.db_table, "admin_tokens")

    def test_admin_es_considerado_autenticado_por_drf(self):
        self.assertTrue(build_admin_with_password().is_authenticated)


class CreateAdminCommandTests(SimpleTestCase):
    @patch("apps.authentication.management.commands.create_admin.Admin")
    def test_crea_admin_con_password_hasheado(self, admin_model):
        admin_model.objects.update_or_create.return_value = (Mock(email="nuevo@avisti.com"), True)
        stdout = StringIO()

        call_command(
            "create_admin",
            "--email",
            "nuevo@avisti.com",
            "--name",
            "Nuevo",
            "--password",
            "Secreta#2026",
            stdout=stdout,
        )

        create_kwargs = admin_model.objects.update_or_create.call_args.kwargs
        self.assertEqual(create_kwargs["email"], "nuevo@avisti.com")
        self.assertEqual(create_kwargs["defaults"]["name"], "Nuevo")
        self.assertNotEqual(create_kwargs["defaults"]["password"], "Secreta#2026")
        self.assertTrue(check_password("Secreta#2026", create_kwargs["defaults"]["password"]))
        self.assertIn("creado", stdout.getvalue())

    @patch("apps.authentication.management.commands.create_admin.Admin")
    def test_actualiza_admin_existente(self, admin_model):
        admin_model.objects.update_or_create.return_value = (Mock(email="nuevo@avisti.com"), False)
        stdout = StringIO()

        call_command("create_admin", "--email", "nuevo@avisti.com", "--password", "Secreta#2026", stdout=stdout)

        self.assertIn("actualizado", stdout.getvalue())

    @patch("apps.authentication.management.commands.create_admin.Admin")
    def test_sin_password_ni_variable_de_entorno_falla(self, admin_model):
        with patch.dict("os.environ", {"ADMIN_PASSWORD": ""}), self.assertRaises(CommandError):
            call_command("create_admin", "--email", "nuevo@avisti.com", stdout=StringIO())

        admin_model.objects.update_or_create.assert_not_called()

    @patch("apps.authentication.management.commands.create_admin.Admin")
    def test_toma_password_de_variable_de_entorno(self, admin_model):
        admin_model.objects.update_or_create.return_value = (Mock(email="nuevo@avisti.com"), True)

        with patch.dict("os.environ", {"ADMIN_PASSWORD": "DesdeEntorno#2026"}):
            call_command("create_admin", "--email", "nuevo@avisti.com", stdout=StringIO())

        hashed = admin_model.objects.update_or_create.call_args.kwargs["defaults"]["password"]
        self.assertTrue(check_password("DesdeEntorno#2026", hashed))