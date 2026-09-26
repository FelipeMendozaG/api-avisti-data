# Contexto del Proyecto — API Avistidata Chepita

## 1. Visión General

API REST construida con **Django + Django REST Framework** que recibe archivos **Excel (.xlsx), CSV y JSON**, convierte los registros en **un solo string JSON** y los envía como parámetro a **procedimientos almacenados de MySQL** (toda la escritura de importación sigue ocurriendo dentro de los SP). Además expone **autenticación de administradores por token** (`Authorization: Bearer`) y **endpoints GET protegidos** de catálogo, cargas y bitácora que leen las tablas existentes mediante modelos Django con `managed = False`.

- **Lenguaje/Runtime:** Python ≥ 3.12
- **Framework:** Django (API pura, sin templates ni admin)
- **Base de datos:** MySQL (vía `mysqlclient` + `django.db.backends.mysql`)
- **Persistencia:** escritura de importación solo vía `cursor.callproc`; lectura de listados vía ORM (modelos `managed = False`)

---

## 2. Estructura de Carpetas

```
api-avistidata-chepita/
├── apps/
│   ├── authentication/                 # Autenticación de administradores por token
│   │   ├── models.py                   # Admin (admins) y AdminToken (admin_tokens), managed = False
│   │   ├── authentication.py           # AdminTokenAuthentication (Authorization: Bearer <token>)
│   │   ├── management/commands/        # create_admin (make_password)
│   │   └── api/                        # serializers.py, views.py (login/logout), urls.py, exceptions.py
│   ├── catalog/                        # Catálogo de solo lectura
│   │   ├── models.py                   # Product (products) y Equipment (equipments), managed = False
│   │   └── api/                        # serializers.py, views.py (GET protegidos), urls.py
│   └── imports/
│       ├── __init__.py
│       ├── apps.py                     # AppConfig de Django ("apps.imports")
│       ├── exceptions.py               # Excepciones de dominio
│       ├── models.py                   # DataLoad y ProcedureExecutionLog, managed = False
│       ├── api/                        # Capa HTTP (DRF)
│       │   ├── views.py                # 3 vistas APIView de importación (Excel, CSV, JSON)
│       │   ├── list_views.py           # GET protegidos de data-loads y logs
│       │   ├── list_serializers.py     # Serializers de solo lectura de cargas y bitácora
│       │   ├── serializers.py          # Validación del body JSON
│       │   └── urls.py                 # Rutas de la app
│       ├── parsers/                    # Lectura y transformación de archivos
│       │   ├── excel_parser.py         # openpyxl → list[dict] (mapeo de columnas)
│       │   └── csv_parser.py           # CSV UTF-8 → list[dict]
│       ├── services/
│       │   └── import_service.py       # Serializa a JSON string y orquesta el repo
│       ├── repositories/
│       │   └── import_repository.py    # callproc contra MySQL (cursos)
│       ├── validators/
│       │   └── import_validator.py     # validate_records() (disponible, no activo)
│       └── migrations/                 # Vacía (no hay modelos gestionados por migrate)
├── config/
│   ├── settings.py                     # Django settings desde .env
│   ├── urls.py                         # Router raíz: api/v1/auth/, api/v1/ y api/v1/import/
│   └── wsgi.py                         # Entry point WSGI
├── tests/
│   ├── support.py                      # Utilidades compartidas (entidades y endpoint protegido)
│   ├── test_imports.py                 # pytest (mockea el repository, sin MySQL)
│   ├── test_authentication.py          # login/logout, header Bearer, comando create_admin
│   ├── test_catalog.py                 # GET /products/ y /equipments/
│   ├── test_imports_lists.py           # GET /import/data-loads/ y /import/logs/
│   └── test_cors.py                    # Preflight OPTIONS y cabeceras CORS
├── manage.py
├── Dockerfile                          # python:3.12-slim + runserver
├── postman/
│   └── API-Avistidata-Chepita.postman_collection.json   # 22 requests (v2.1, importable en Postman/Bruno)
├── pyproject.toml                      # Dependencias y config pytest
├── README.md
├── .env / .env.example
└── .gitignore / .dockerignore
```

### Responsabilidad de cada capa

| Carpeta / archivo | Función |
|---|---|
| `config/` | Proyecto Django: settings (lee `.env` con `python-dotenv`), enrutado raíz y WSGI. |
| `apps/authentication/` | Modelos de solo consulta (`admins`, `admin_tokens`), `AdminTokenAuthentication` (`Authorization: Bearer <token>`), endpoints `login`/`logout` y comando `create_admin` (usa `make_password`). |
| `apps/catalog/` | Modelos de solo consulta `products` y `equipments` + endpoints GET protegidos con filtros `?search=` y `?product_id=`. |
| `apps/imports/models.py` | Modelos de solo consulta (`data_loads`, `procedure_execution_logs`), todos con `managed = False`. |
| `apps/imports/api/list_views.py` | Endpoints GET protegidos `/api/v1/import/data-loads/` y `/api/v1/import/logs/`. No modifican el flujo de importación. |
| `apps/imports/api/` | Capa de transporte HTTP: parsers de DRF (multipart/form/json), manejo de errores y códigos de estado, y el serializer de validación para el endpoint JSON. |
| `apps/imports/parsers/` | Convierte binarios de archivos en `list[dict]`. Excel valida extensión/tamaño/hoja y normaliza tipos (fechas → `DD/MM/YYYY`, bool → `VERDADERO/FALSO`, alias de encabezados). CSV valida encoding UTF-8 y separador configurable. |
| `apps/imports/services/` | `ImportService`: recibe los registros, hace `json.dumps(records, ensure_ascii=False)` y delega al repository. Punto de extensión para batching futura. |
| `apps/imports/repositories/` | `ImportRepository`: ejecuta `cursor.callproc` con el nombre de SP desde settings, consume resultsets y (solo Excel) lee los parámetros OUT (`p_load_id`, `p_status`). Envuelve errores en `ImportRepositoryError`. |
| `apps/imports/validators/` | `validate_records()`: valida filas vacías, columnas requeridas y valores nulos. **Nota:** actualmente ninguno de los endpoints la invoca (decisión de diseño documentada en README). |
| `postman/` | Colección Postman v2.1 (importable en Bruno) con los 22 requests de la API, variables de colección (`{{base_url}}`, `{{token}}`, filtros) y scripts de test del contrato `{success, message, data|errors}`. |

| `apps/imports/exceptions.py` | `ImportValidationError` (→ HTTP 400) e `ImportRepositoryError` (→ HTTP 502). |
| `tests/` | Suite pytest: parsers, service y endpoints con `ImportRepository` mockeado (no requiere MySQL). |

---

## 3. Dependencias (`pyproject.toml`)

**Runtime:**

| Paquete | Versión | Uso |
|---|---|---|
| `Django` | >=5.0,<7.0 | Framework web y conexión MySQL (sin ORM de modelos). |
| `djangorestframework` | >=3.15,<4.0 | APIView, parsers, serializers, `APIClient` de pruebas. |
| `django-cors-headers` | >=4.3,<5.0 | `CorsMiddleware` y settings CORS (`Access-Control-Allow-*`) para que cualquier aplicación consuma la API desde el navegador. |
| `mysqlclient` | >=2.2,<3.0 | Driver C de MySQL para la conexión de Django. |
| `openpyxl` | >=3.1,<4.0 | Lectura de archivos `.xlsx` (modo `read_only=True, data_only=True`). |
| `python-dotenv` | >=1.0,<2.0 | Carga de `.env` en `config/settings.py`. |

**Opcionales (dev/test):** `pytest` (>=8,<9) y `pytest-django` (>=4.8,<5.0) — configurados con `DJANGO_SETTINGS_MODULE = config.settings`.

**Instalación:** `pip install -e ".[test]"`

---

## 4. Configuración (variables de `.env`)

| Variable | Default / ejemplo | Uso |
|---|---|---|
| `DJANGO_SECRET_KEY` | `change-me` | Secret de Django. |
| `DJANGO_DEBUG` | `True` | Debug on/off. |
| `DJANGO_ALLOWED_HOSTS` | `127.0.0.1,localhost` | Hosts permitidos (separados por coma). |
| `DB_NAME` / `DB_USER` / `DB_PASSWORD` | `avistidata` / `root` | Credenciales MySQL. |
| `DB_HOST` / `DB_PORT` | `127.0.0.1` / `3306` | Conexión MySQL (en Docker: `host.docker.internal`). |
| `IMPORT_MAX_FILE_SIZE_BYTES` | `10485760` (10 MB) | Límite de tamaño para Excel y CSV. |
| `IMPORT_CSV_DELIMITER` | `,` | Separador del CSV (1 carácter). |
| `IMPORT_EXCEL_SHEET_NAME` | `MOVIMIENTO` | Hoja a leer del Excel; vacío = primera hoja. |
| `IMPORT_REQUIRED_COLUMNS` | lista de 20 columnas | Reservada para reglas futuras (no se usa en los endpoints). |
| `SP_IMPORT_EXCEL` | `sp_importar_excel` | Nombre del SP de Excel. |
| `SP_IMPORT_CSV` | `sp_importar_csv` | Nombre del SP de CSV. |
| `SP_IMPORT_JSON` | `sp_importar_json` | Nombre del SP de JSON. |
| `AUTH_TOKEN_TTL_HOURS` | `24` | Vigencia de los tokens emitidos por `/api/v1/auth/login/`. |
| `CORS_ALLOW_ALL_ORIGINS` | `True` | Permitir cualquier origen (`Access-Control-Allow-Origin: *`). |
| `CORS_ALLOWED_ORIGINS` | vacío | Lista blanca separada por coma; se usa cuando `CORS_ALLOW_ALL_ORIGINS=False`. |
| `CORS_ALLOW_CREDENTIALS` | `False` | Cookies / HTTP Basic. Si es `True` se devuelve el origen exacto en lugar de `*`. |
| `CORS_PREFLIGHT_MAX_AGE` | `86400` | Segundos de caché del preflight `OPTIONS`. |

Otros detalles de settings: `MIDDLEWARE = [corsheaders.middleware.CorsMiddleware, SecurityMiddleware]`, `INSTALLED_APPS = [corsheaders, rest_framework, apps.authentication, apps.catalog, apps.imports]`, `REST_FRAMEWORK = {"UNAUTHENTICATED_USER": None, "EXCEPTION_HANDLER": "apps.authentication.api.exceptions.api_exception_handler"}` y `AUTH_TOKEN_TTL_HOURS`. `CorsMiddleware` va primero para agregar `Access-Control-Allow-*` a **todas** las respuestas (200, 400, 401, 502) y para responder los preflight `OPTIONS` **antes** de llegar a las vistas: el navegador nunca recibe 401 en el preflight y no hace falta token para ese `OPTIONS`. La autenticación por token sigue siendo obligatoria en los endpoints protegidos. El `EXCEPTION_HANDLER` reformatea **solo** los errores 401/403 con el formato estándar; el resto de errores de DRF (por ejemplo, los de importación) se devuelven igual que antes. Sin TEMPLATES y sin las apps admin/auth/session/contenttypes: las contraseñas se validan con `django.contrib.auth.hashers` sin instalar `django.contrib.auth`.

---

## 5. Endpoints implementados

Base URL: `http://localhost:8000/api/v1/` (definida en `config/urls.py`).

- `/api/v1/auth/` → `apps.authentication.api.urls`
- `/api/v1/` → `apps.catalog.api.urls` (`products/`, `equipments/`)
- `/api/v1/import/` → `apps.imports.api.urls`

Los endpoints de **consulta** (login/logout no) exigen `Authorization: Bearer <token>`; los tres de **importación** siguen siendo públicos y con el mismo comportamiento que antes de este cambio.

### 5.1 `POST /api/v1/import/excel/` — Importar Excel
- **Content-Type:** `multipart/form-data`
- **Campos:** `file` (`.xlsx`, máx. 10 MB), `data_source` (requerido), `loaded_by` (requerido).
- Lee la hoja `IMPORT_EXCEL_SHEET_NAME` (o la primera si no está configurada).
- Cada registro sale con claves fijas: `Registro`, `Co`, `Serie`, `Descripcion`, `Comienzo`, `Vencimiento`, `Cliente`, `Usuario`, `Fechareg`, `EstadoArtA`, `GrupoKarde`, `Cierre`.
- Alias de encabezados (case-insensitive): `Codigo→Co`, `EstadoArtAlqui→EstadoArtA`, `GrupoKardex→GrupoKarde`.
- Normalización: fechas → `DD/MM/YYYY HH:MM` (date puro → `DD/MM/YYYY`), `Decimal→float`, `Registro` float entero → `int`, bool `Cierre` → `VERDADERO/FALSO`.
- Llama a `sp_importar_excel(p_data_source, p_file_name, p_loaded_by, p_json_data, OUT p_load_id, OUT p_status)`; `file.name` se envía como `p_file_name` y los OUT se leen con `SELECT @_sp_4, @_sp_5`.
- **200:** `{success, message, data: {records_received, records_processed, records_rejected, procedure_result: {load_id, status, ...}}}`
- **400** si falta `data_source`/`loaded_by`, archivo inválido/corrupto/hoja inexistente. **502** si falla el SP.

### 5.2 `POST /api/v1/import/csv/` — Importar CSV
- **Content-Type:** `multipart/form-data`, campo `file` (`.csv`).
- Encoding esperado UTF-8 (acepta BOM, `utf-8-sig`); separador de `IMPORT_CSV_DELIMITER`.
- Cada registro es un dict con los encabezados del archivo tal cual (no valida columnas; archivo vacío → lista vacía).
- Llama a `sp_importar_csv(p_json_data)` con un único parámetro posicional.
- **200 / 400 (extensión, encoding, tamaño) / 502 (fallo SP).**

### 5.3 `POST /api/v1/import/json/` — Importar JSON
- **Content-Type:** `application/json`; acepta un objeto o una lista de objetos (los envuelve internamente en `{"records": ...}` y valida con `JSONImportSerializer`).
- Ejemplo:
  ```json
  {"documento": "12345678", "nombre": "Juan Pérez", "monto": 150.5}
  ```
- Llama a `sp_importar_json(p_json_data)` con un único parámetro posicional.
- **200 / 400 (body malformado o no-dict / lista vacía) / 502 (fallo SP).**

### 5.4 `POST /api/v1/auth/login/` — Iniciar sesión (público)
- Body JSON: `{"email": "...", "password": "..."}` (validado con `LoginSerializer`).
- Busca en `Admin.objects.filter(email=...)` y valida con `check_password`; si el email no existe o la contraseña no coincide → **401** `{"success": false, "message": "Credenciales inválidas", "errors": {"credentials": "invalid"}}`.
- Genera `secrets.token_hex(32)` (64 caracteres) y lo persiste con `AdminToken.objects.create(...)`, con `expires_at = now() + AUTH_TOKEN_TTL_HOURS`.
- **200:** `{"success": true, "message": "Autenticación exitosa", "data": {"token": "…", "expires_at": "…"}}`.
- **400** si faltan campos o el email es inválido.

### 5.5 `POST /api/v1/auth/logout/` — Cerrar sesión (protegido)
- Requiere `Authorization: Bearer <token>`; elimina la fila del token usado (`request.auth.delete()`).
- **200:** `{"success": true, "message": "Sesión finalizada correctamente", "data": null}`.

### 5.6 `GET /api/v1/products/` y `GET /api/v1/equipments/` — Catálogo (protegidos)
- `ProductListView`: `Product.objects.all().order_by("product_id")`, filtro opcional `?search=` (código, nombre o descripción con `icontains`).
- `EquipmentListView`: `Equipment.objects.select_related("product").all().order_by("equipment_id")`, filtro opcional `?product_id=` (entero; valor no numérico → **400** `{"errors": {"product_id": "invalid"}}`).
- **200:** `{"success": true, "message": "...", "data": [ … ]}` con `ProductSerializer` / `EquipmentSerializer`.

### 5.7 `GET /api/v1/import/data-loads/` y `GET /api/v1/import/logs/` — Cargas y bitácora (protegidos)
- `DataLoadListView`: `DataLoad.objects.all().order_by("-load_date")`.
- `ProcedureExecutionLogListView`: `ProcedureExecutionLog.objects.all().order_by("-created_at")`, filtro opcional `?load_id=` (valor no numérico → **400** `{"errors": {"load_id": "invalid"}}`).
- Ambos usan `DataLoadSerializer` / `ProcedureExecutionLogSerializer` (solo lectura) y **no intervienen** en el flujo de importación.

### Formato de respuesta común
- Éxito: `{"success": true, "message": "...", "data": {...}}` (importación: `"Información procesada correctamente"`; consultas: mensaje propio de cada endpoint).
- Error: `{"success": false, "message": "...", "errors": {...}}` con 400/401/404/415/502.

---

## 6. Flujo de datos (pipeline)

```
Request HTTP
   │
   ▼
View (api/views.py) ── valida campos base (solo Excel: data_source/loaded_by)
   │
   ▼
Parser (parsers/) ── archivo → list[dict]  (valida extensión, tamaño, encoding, hoja)
   │
   ▼
ImportService (services/) ── json.dumps(records, ensure_ascii=False) → un solo string JSON
   │
   ▼
ImportRepository (repositories/) ── connection.cursor().callproc(sp_name, [...])
   │                                consume resultsets y lee OUT (solo Excel)
   ▼
MySQL Stored Procedure (sp_importar_excel / _csv / _json)
```

Los registros se mantienen **en memoria** como `list[dict]` y se envían **todo en un solo JSON string**; no hay validación de columnas/filas en el flujo actual (`validators/` queda disponible).

---

## 7. Manejo de errores

| Excepción | Origen | HTTP | Respuesta |
|---|---|---|---|
| `ImportValidationError` | Parsers / serializer | 400 | `{success, message, errors}` con detalle (ej. `{"file": "invalid_extension"}`). |
| `ImportRepositoryError` | Repository | 502 | `{"errors": {"database": "processing_error"}}` + log con `logger.exception`. |
| Errores DRF (parse, 404, 405…) | `handle_exception` | original | Se envuelve en `{success, message, errors: {"request": ...}}`. |
| `AuthenticationFailed` | `AdminTokenAuthentication` | 401 | `{"success": false, "message": "Token inválido o expirado", "errors": {"detail": "…"}}` + header `WWW-Authenticate: Bearer`. Se dispara si falta el header, el esquema no es `Bearer`, el token no existe o expiró. |
| `NotAuthenticated` | `permission_classes` | 401 | Mismo formato estándar con `"Credenciales de autenticación no proporcionadas"`. |

---

## 8. Pruebas (`tests/`)

Suite con pytest que **no requiere MySQL** (mockea `ImportRepository`, el ORM y la autenticación con `Mock`/`patch`):

- **`test_imports.py` (existente, intacto):** Excel válido → mapeo/normalización exacta; CSV UTF-8 con acentos y comillas; archivo vacío → lista vacía; columnas faltantes se aceptan; `process`/`process_excel` envían el JSON string y metadatos exactamente como al repository; `callproc` con parámetros posicionales y lectura de OUT; comportamiento HTTP de los tres endpoints (200, multipart, JSON malformado → 400). Ninguno envía token: prueban que los endpoints de importación siguen siendo públicos.
- **`test_authentication.py`:** login con credenciales válidas (token de 64 caracteres, `check_password` real contra un hash generado con `make_password`, `expires_at` ≈ 24 h), credenciales inválidas → 401, payload incompleto → 400; logout elimina el token; los 4 endpoints protegidos devuelven 401 sin header, con esquema incorrecto, con token inexistente/expirado; la autenticación usa `select_related("admin")` y filtra por `token` y `expires_at__gt`; `create_admin` hashea con `make_password` (y toma la contraseña de `ADMIN_PASSWORD`).
- **`test_catalog.py`:** `GET /products/` y `/equipments/` con token → 200 y estructura estándar, valores serializados, filtros `?search=` y `?product_id=`, y 400 para `product_id` no numérico.
- **`test_imports_lists.py`:** `GET /import/data-loads/` y `/import/logs/` con token → 200 con orden `-load_date` / `-created_at`, filtro `?load_id=` y 400 para `load_id` no numérico.
- **`test_cors.py`:** preflight `OPTIONS` de los 4 listados protegidos y de los POST multipart → 200/204 sin token, con `Access-Control-Allow-Headers: authorization, content-type` y `Access-Control-Max-Age: 86400`; cabeceras CORS presentes en respuestas 200, en los 401 y en los endpoints públicos de importación; ausencia de cabecera cuando no hay `Origin`; y modo lista blanca (`CORS_ALLOW_ALL_ORIGINS=False`) donde solo el origen permitido recibe `Access-Control-Allow-Origin`.
- **`support.py`:** constructores de entidades sin persistencia (`build_product`, `build_equipment`, `build_data_load`, `build_log`, `build_admin...`) y `ProtectedEndpointTestCase`, que simula un token Bearer vigente.

Ejecutar: `pytest`

**Nota sobre los modelos:** todos usan `managed = False`, por lo que `migrate` nunca crea ni altera las tablas reales. `apps/imports` conserva su carpeta `migrations/` (vacía), así que `makemigrations` propone una migración inicial para `DataLoad`/`ProcedureExecutionLog`; aplicarla (o ignorarla) no toca MySQL. `apps/authentication` y `apps/catalog` no tienen carpeta `migrations/`, de modo que Django las trata como apps sin migraciones.

---

## 9. Ejecución y Despliegue

**Local:**
```powershell
pip install -e ".[test]"
python manage.py check
python manage.py runserver
```

**Docker:**
```powershell
docker build -t api-avistidata-chepita .
docker run --rm -p 8000:8000 --env-file .env api-avistidata-chepita
```
El `Dockerfile` instala `build-essential`, `default-libmysqlclient-dev` y `pkg-config` (necesarios para compilar `mysqlclient`) y arranca con `runserver 0.0.0.0:8000`. En Docker Desktop usar `DB_HOST=host.docker.internal` si MySQL corre en el host.

---

## 10. Puntos de extensión / pendientes conocidos

- `IMPORT_REQUIRED_COLUMNS` y `validators/import_validator.py` están listos pero **no se invocan** en los endpoints (reglas de negocio futuras).
- `ImportService` es el punto previsto para añadir **procesamiento por lotes** si el volumen real lo requiere.
- Los SP actuales reciben **un solo parámetro posicional** (el JSON string); si el contrato real de MySQL añade más parámetros, ajustar `ImportRepository`.
- La tabla `admins` está vacía en `db_avisti`: crear el primer administrador con `python manage.py create_admin --email … --password …` (o `ADMIN_PASSWORD`) antes de poder usar `/api/v1/auth/login/`.
- No hay paginación en los listados (`/products/`, `/equipments/`, `/data-loads/`, `/logs/`) ni revocación masiva de tokens (solo logout del token actual); tampoco se purgan tokens expirados automáticamente.
- No hay logging estructurado más allá de `logger.exception` en fallos de SP.

