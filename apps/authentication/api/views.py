import secrets
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.hashers import check_password
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.authentication.api.serializers import LoginSerializer
from apps.authentication.authentication import AdminTokenAuthentication
from apps.authentication.models import Admin, AdminToken

TOKEN_TTL_HOURS = getattr(settings, "AUTH_TOKEN_TTL_HOURS", 24)


class LoginView(APIView):
    """POST /api/v1/auth/login/ — público: valida credenciales y emite un token."""

    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"success": False, "message": "Datos inválidos", "errors": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        admin = Admin.objects.filter(email=serializer.validated_data["email"]).first()
        if admin is None or not check_password(serializer.validated_data["password"], admin.password):
            return Response(
                {"success": False, "message": "Credenciales inválidas", "errors": {"credentials": "invalid"}},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        expires_at = timezone.now() + timedelta(hours=TOKEN_TTL_HOURS)
        admin_token = AdminToken.objects.create(
            admin=admin,
            token=secrets.token_hex(32),
            expires_at=expires_at,
        )
        return Response(
            {
                "success": True,
                "message": "Autenticación exitosa",
                "data": {"token": admin_token.token, "expires_at": admin_token.expires_at},
            }
        )


class LogoutView(APIView):
    """POST /api/v1/auth/logout/ — protegido: invalida el token usado en la petición."""

    authentication_classes = [AdminTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        request.auth.delete()
        return Response({"success": True, "message": "Sesión finalizada correctamente", "data": None})