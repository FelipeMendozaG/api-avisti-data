from django.utils import timezone
from rest_framework import exceptions
from rest_framework.authentication import BaseAuthentication, get_authorization_header

from apps.authentication.models import AdminToken


class AdminTokenAuthentication(BaseAuthentication):
    """Autenticación de administradores mediante el header `Authorization: Bearer <token>`."""

    keyword = "Bearer"
    error_message = "Token inválido o expirado"

    def authenticate(self, request):
        header = get_authorization_header(request)
        if not header:
            raise exceptions.AuthenticationFailed(self.error_message)

        parts = header.decode("utf-8", errors="replace").split()
        if len(parts) != 2 or parts[0].lower() != self.keyword.lower() or not parts[1]:
            raise exceptions.AuthenticationFailed(self.error_message)

        admin_token = (
            AdminToken.objects.select_related("admin")
            .filter(token=parts[1], expires_at__gt=timezone.now())
            .first()
        )
        if admin_token is None:
            raise exceptions.AuthenticationFailed(self.error_message)

        return (admin_token.admin, admin_token)

    def authenticate_header(self, request):
        """Necesario para que DRF responda HTTP 401 (en lugar de 403) ante fallos de autenticación."""
        return self.keyword
