from rest_framework import exceptions
from rest_framework.response import Response
from rest_framework.views import exception_handler


def api_exception_handler(exc, context):
    """Devuelve los errores de autenticación/autorización con el formato estándar de la API.

    Éxito: {"success": true,  "message": "...", "data": ...}
    Error: {"success": false, "message": "...", "errors": ...}

    El resto de excepciones de DRF se retornan sin cambios para no alterar el
    comportamiento de los endpoints existentes de importación.
    """
    response = exception_handler(exc, context)
    if response is None or response.status_code not in (401, 403):
        return response

    if isinstance(exc, exceptions.NotAuthenticated):
        message = "Credenciales de autenticación no proporcionadas"
    elif response.status_code == 401:
        message = str(exc.detail)
    else:
        message = "No tiene permisos para realizar esta acción"

    return Response(
        {"success": False, "message": message, "errors": {"detail": str(exc.detail)}},
        status=response.status_code,
        headers=response.headers,
    )
