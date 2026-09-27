import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "development-only-key")
DEBUG = os.getenv("DJANGO_DEBUG", "False").strip().lower() in {"true", "1", "yes", "on"}


def _build_allowed_hosts() -> list:
    """ALLOWED_HOSTS robusto para App Engine.

    - Si DJANGO_ALLOWED_HOSTS contiene "*", se devuelve ["*"] (válido con
      DEBUG=False y evita 400 DisallowedHost en el readiness check).
    - Si está vacío y estamos en App Engine (GAE_ENV), se permite "*"
      como fallback seguro para no tumbar el deploy.
    - En local se usa lo configurado o localhost por defecto.
    """
    raw = os.getenv("DJANGO_ALLOWED_HOSTS", "")
    hosts = [h.strip() for h in raw.split(",") if h.strip()]
    if "*" in hosts:
        return ["*"]
    if hosts:
        return hosts
    # Fallback: en App Engine nunca dejar la lista vacía (400 -> 503).
    if os.getenv("GAE_ENV") or os.getenv("GOOGLE_CLOUD_PROJECT"):
        return ["*"]
    return ["127.0.0.1", "localhost"]


ALLOWED_HOSTS = _build_allowed_hosts()

# App Engine termina TLS en el balanceador y reenvía http interno.
# Sin esto, request.is_secure() y redirects fallan detrás del proxy.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
USE_X_FORWARDED_HOST = True

INSTALLED_APPS = [
    "corsheaders",
    "rest_framework",
    "apps.authentication",
    "apps.catalog",
    "apps.imports",
    "apps.donations",
]

# CorsMiddleware debe ir lo más alto posible para que las cabeceras CORS se
# agreguen también a las respuestas de error (401, 400, 502) y para que las
# peticiones preflight OPTIONS se respondan sin llegar a las vistas.
MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
]
ROOT_URLCONF = "config.urls"
TEMPLATES = []
WSGI_APPLICATION = "config.wsgi.application"

def _is_gae() -> bool:
    """True si corremos dentro de App Engine Standard."""
    return bool(os.getenv("GAE_ENV") or os.getenv("GAE_APPLICATION"))


def _build_databases():
    """Construye DATABASES con modo dual: socket Unix en Cloud SQL o TCP en local.

    - Desplegado (App Engine con Cloud SQL): si existe `DB_SOCKET_PATH`
      (o `CLOUD_SQL_CONNECTION_NAME`), se usa el socket Unix
      `/cloudsql/PROYECTO:REGION:INSTANCIA` y se ignoran `DB_HOST`/`DB_PORT`.
    - Local: sin socket configurado, se usa TCP con `DB_HOST`/`DB_PORT`.
    - `DB_DATABASE` se acepta como alias legacy de `DB_NAME`.
    - `DB_ENGINE` permite sobrescribir el motor (por defecto MySQL).
    """

    db_name = os.getenv("DB_NAME", "").strip() or os.getenv("DB_DATABASE", "").strip()
    db_user = os.getenv("DB_USER", "")
    db_password = os.getenv("DB_PASSWORD", "")
    db_engine = os.getenv("DB_ENGINE", "django.db.backends.mysql").strip() or "django.db.backends.mysql"

    socket_path = os.getenv("DB_SOCKET_PATH", "").strip()
    connection_name = os.getenv("CLOUD_SQL_CONNECTION_NAME", "").strip()
    if not socket_path and connection_name:
        # Permite configurar solo el connection name y derivar el socket.
        socket_path = connection_name if connection_name.startswith("/") else f"/cloudsql/{connection_name}"

    # Opciones comunes MySQL: utf8mb4 + timeout corto para no colgar el
    # readiness check si Cloud SQL no responde.
    options = {
        "charset": "utf8mb4",
        "connect_timeout": 10,
        "init_command": "SET sql_mode='STRICT_TRANS_TABLES'",
    }

    if socket_path:
        # Modo Cloud SQL: el backend MySQL de Django trata un HOST que empieza
        # con "/" como unix_socket (host=localhost). PORT se deja vacío porque
        # se ignora con socket Unix.
        return {
            "default": {
                "ENGINE": db_engine,
                "NAME": db_name,
                "USER": db_user,
                "PASSWORD": db_password,
                "HOST": socket_path,
                "PORT": "",
                "OPTIONS": options,
                # 0 = no persistir entre requests (evita "MySQL gone away"
                # cuando el escalador mata conexiones idle).
                "CONN_MAX_AGE": 0,
                "CONN_HEALTH_CHECKS": True,
            }
        }

    # Fallback: si alguien puso el socket directamente en DB_HOST, tratarlo igual.
    db_host = os.getenv("DB_HOST", "127.0.0.1").strip() or "127.0.0.1"
    db_port = os.getenv("DB_PORT", "3306").strip()
    if db_host.startswith("/") or db_host.startswith("cloudsql/"):
        socket_path = db_host if db_host.startswith("/") else f"/{db_host}"
        return {
            "default": {
                "ENGINE": db_engine,
                "NAME": db_name,
                "USER": db_user,
                "PASSWORD": db_password,
                "HOST": socket_path,
                "PORT": "",
                "OPTIONS": options,
                "CONN_MAX_AGE": 0,
                "CONN_HEALTH_CHECKS": True,
            }
        }

    # Modo local / TCP clásico.
    return {
        "default": {
            "ENGINE": db_engine,
            "NAME": db_name,
            "USER": db_user,
            "PASSWORD": db_password,
            "HOST": db_host,
            "PORT": db_port,
            "OPTIONS": options,
            "CONN_MAX_AGE": 0,
            "CONN_HEALTH_CHECKS": True,
        }
    }


DATABASES = _build_databases()

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Logs a stdout para que aparezcan en Cloud Logging (gcloud app logs tail).
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {"format": "%(asctime)s %(levelname)s %(name)s: %(message)s"},
    },
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "default"},
    },
    "root": {"handlers": ["console"], "level": os.getenv("DJANGO_LOG_LEVEL", "INFO")},
    "loggers": {
        "django": {"handlers": ["console"], "level": "INFO", "propagate": False},
        "django.request": {"handlers": ["console"], "level": "INFO", "propagate": False},
        "gunicorn.error": {"handlers": ["console"], "level": "INFO", "propagate": False},
    },
}
REST_FRAMEWORK = {
    "UNAUTHENTICATED_USER": None,
    "EXCEPTION_HANDLER": "apps.authentication.api.exceptions.api_exception_handler",
}
AUTH_TOKEN_TTL_HOURS = int(os.getenv("AUTH_TOKEN_TTL_HOURS", "24"))
# Paginación de los endpoints de listado (products, equipments y data-loads).
PAGINATION_DEFAULT_PAGE_SIZE = int(os.getenv("PAGINATION_DEFAULT_PAGE_SIZE", "20"))
PAGINATION_MAX_PAGE_SIZE = int(os.getenv("PAGINATION_MAX_PAGE_SIZE", "100"))
IMPORT_MAX_FILE_SIZE_BYTES = int(os.getenv("IMPORT_MAX_FILE_SIZE_BYTES", "10485760"))
IMPORT_CSV_DELIMITER = os.getenv("IMPORT_CSV_DELIMITER", ",")
IMPORT_EXCEL_SHEET_NAME = os.getenv("IMPORT_EXCEL_SHEET_NAME") or None
IMPORT_REQUIRED_COLUMNS = [
    column.strip()
    for column in os.getenv("IMPORT_REQUIRED_COLUMNS", "").split(",")
    if column.strip()
]
STORED_PROCEDURES = {
    "excel": os.getenv("SP_IMPORT_EXCEL", "sp_importar_excel"),
    "csv": os.getenv("SP_IMPORT_CSV", "sp_importar_csv"),
    "json": os.getenv("SP_IMPORT_JSON", "sp_importar_json"),
}

# --- CORS -------------------------------------------------------------------
# Abierto por defecto para que cualquier aplicación (web, móvil, otra API) pueda
# consumir la API desde el navegador. La autenticación sigue siendo obligatoria
# en los endpoints protegidos mediante `Authorization: Bearer <token>`.
CORS_ALLOW_ALL_ORIGINS = os.getenv("CORS_ALLOW_ALL_ORIGINS", "True").lower() == "true"
CORS_ALLOWED_ORIGINS = [
    origin.strip() for origin in os.getenv("CORS_ALLOWED_ORIGINS", "").split(",") if origin.strip()
]
# Con credenciales activadas el navegador exige un origen exacto (no "*"); solo
# es necesario si el cliente depende de cookies o de HTTP Basic.
CORS_ALLOW_CREDENTIALS = os.getenv("CORS_ALLOW_CREDENTIALS", "False").lower() == "true"
# `authorization` es imprescindible porque el token viaja en el header Bearer;
# `content-type` es necesario para JSON y para los POST multipart de importación.
CORS_ALLOW_HEADERS = [
    "accept",
    "accept-encoding",
    "authorization",
    "content-type",
    "dnt",
    "origin",
    "user-agent",
    "x-csrftoken",
    "x-requested-with",
]
CORS_ALLOW_METHODS = ["DELETE", "GET", "OPTIONS", "PATCH", "POST", "PUT"]
# Caché del preflight en segundos (evita un OPTIONS por cada petición).
CORS_PREFLIGHT_MAX_AGE = int(os.getenv("CORS_PREFLIGHT_MAX_AGE", "86400"))