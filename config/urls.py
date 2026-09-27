from django.urls import include, path

from config.healthz import healthz

urlpatterns = [
    # Endpoints de salud para readiness/liveness checks de App Engine.
    # Deben responder 200 SIN tocar la base de datos.
    path("healthz/", healthz),
    path("healthz", healthz),
    path("api/v1/auth/", include("apps.authentication.api.urls")),
    path("api/v1/", include("apps.catalog.api.urls")),
    path("api/v1/import/", include("apps.imports.api.urls")),
    path("api/v1/admin/", include("apps.donations.api.urls")),
]
