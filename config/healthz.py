"""Vista de salud ligera para los readiness/liveness checks de App Engine.

No toca la base de datos a propósito: el readiness check debe responder
200 aunque Cloud SQL esté caído, para que el diagnóstico (503) distinga
entre "contenedor no arranca" y "DB inaccesible".
"""
from django.http import JsonResponse


def healthz(_request):
    return JsonResponse({"status": "ok"})
