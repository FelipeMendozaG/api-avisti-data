# API Avistidata Chepita

API REST para recibir archivos Excel, CSV o JSON y enviar los registros como un string JSON a procedimientos almacenados de MySQL.

## Requisitos

- Python 3.12 o superior
- MySQL accesible desde la aplicación
- Dependencias del proyecto instaladas con `pip install -e ".[test]"`

## Configuración

1. Copiar `.env.example` como `.env`.
2. Configurar `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST` y `DB_PORT`.
3. Configurar los nombres reales de los procedimientos con `SP_IMPORT_EXCEL`, `SP_IMPORT_CSV` y `SP_IMPORT_JSON`.
4. `IMPORT_REQUIRED_COLUMNS` se conserva como variable disponible para futuras reglas de negocio, pero los endpoints de Excel y CSV no validan columnas ni filas.
5. `AUTH_TOKEN_TTL_HOURS` define la vigencia de los tokens de administrador (24 horas por defecto).
6. CORS está abierto para cualquier origen por defecto (`CORS_ALLOW_ALL_ORIGINS=True`). Para restringirlo, usar `CORS_ALLOWED_ORIGINS` con `CORS_ALLOW_ALL_ORIGINS=False` (ver la sección CORS).

Los nombres y parámetros reales de los procedimientos no fueron proporcionados. La implementación usa un solo parámetro posicional: el string JSON. Ajustar `ImportRepository` cuando el contrato MySQL definitivo incluya más parámetros o una forma de respuesta específica.

## Ejecución

```powershell
python manage.py check
python manage.py runserver
```

## Docker

Construir y ejecutar el contenedor:

```powershell
docker build -t api-avistidata-chepita .
docker run --rm -p 8000:8000 --env-file .env api-avistidata-chepita
```

La API quedará disponible en `http://localhost:8000`. La base MySQL debe ser accesible desde el contenedor; en Docker Desktop, `DB_HOST` puede requerir `host.docker.internal` cuando MySQL corre en el equipo host.

Las pruebas no necesitan conexión MySQL porque simulan el repository y el ORM:

```powershell
pytest
```

- `tests/test_imports.py`: parsers, servicio, repository y endpoints de importación.
- `tests/test_authentication.py`: login/logout, validación del header Bearer, comando `create_admin`.
- `tests/test_catalog.py` y `tests/test_imports_lists.py`: listados protegidos, filtros y estructura de respuesta.
- `tests/test_cors.py`: preflight `OPTIONS` (sin token), cabeceras CORS en respuestas 200/401 y modo lista blanca.
- `tests/support.py`: utilidades compartidas (constructores de entidades y caso base de endpoint protegido).

## Endpoints

Los endpoints de consulta requieren `Authorization: Bearer <token>`. Los de importación permanecen abiertos, con el mismo comportamiento que antes.

### Autenticación

`POST /api/v1/auth/login/` (público) con `{"email": "...", "password": "..."}`. Valida con `check_password` contra la tabla `admins` y emite un token de 64 caracteres vigente `AUTH_TOKEN_TTL_HOURS` horas.

```json
{"success": true, "message": "Autenticación exitosa", "data": {"token": "…", "expires_at": "2026-09-20T08:11:01.856069Z"}}
```

`POST /api/v1/auth/logout/` (protegido) elimina el token usado en la petición.

Para crear administradores (la tabla `admins` no se gestiona con `migrate` porque `managed = False`):

```powershell
python manage.py create_admin --email admin@avisti.com --name "Admin Central" --password "Clave.Segura#2026"
# o bien: ADMIN_PASSWORD="Clave.Segura#2026" python manage.py create_admin --email admin@avisti.com
```

### Catálogo (protegidos)

- `GET /api/v1/products/` con filtro opcional `?search=` (código, nombre o descripción).
- `GET /api/v1/equipments/` con filtro opcional `?product_id=`.

### Cargas y bitácora (protegidos)

- `GET /api/v1/import/data-loads/` ordenado por `-load_date`.
- `GET /api/v1/import/logs/` ordenado por `-created_at`, con filtro opcional `?load_id=`.

Los cinco endpoints responden `{"success": true, "message": "...", "data": [...]}` y devuelven `401` con `{"success": false, "message": "...", "errors": {...}}` cuando el header `Authorization: Bearer <token>` falta, el esquema es incorrecto, el token no existe o expiró.

### Excel

`POST /api/v1/import/excel/` con `multipart/form-data` y los campos `file`, `data_source` y `loaded_by`. El archivo debe ser `.xlsx`; se procesa la hoja configurada en `IMPORT_EXCEL_SHEET_NAME` o la primera hoja. `file.name` se envía como `p_file_name`.

El procedimiento Excel recibe `p_data_source`, `p_file_name`, `p_loaded_by` y `p_json_data` como parámetros de entrada, y devuelve `p_load_id` y `p_status` como parámetros de salida.

El `p_json_data` generado para Excel contiene objetos con estas claves: `Registro`, `Co`, `Serie`, `Descripcion`, `Comienzo`, `Vencimiento`, `Cliente`, `Usuario`, `Fechareg`, `EstadoArtA`, `GrupoKarde` y `Cierre`. Las fechas se envían como `DD/MM/YYYY HH:MM`, los valores booleanos como `VERDADERO` o `FALSO`, y `Codigo`, `EstadoArtAlqui` y `GrupoKardex` se mapean respectivamente a `Co`, `EstadoArtA` y `GrupoKarde`.

### CSV

`POST /api/v1/import/csv/` con `multipart/form-data` y campo `file`. Se espera UTF-8 (también acepta BOM) y el separador se configura con `IMPORT_CSV_DELIMITER`.

### JSON

`POST /api/v1/import/json/` con `Content-Type: application/json`. Puede recibir un objeto o una lista de objetos.

```json
{
  "documento": "12345678",
  "nombre": "Juan Pérez",
  "monto": 150.5
}
```

Los tres endpoints responden con `success`, `message` y `data` en caso de éxito, o `success`, `message` y `errors` en caso de error.

## CORS

La API acepta peticiones desde **cualquier origen** por defecto, mediante `django-cors-headers`:

- `corsheaders.middleware.CorsMiddleware` está **primero** en `MIDDLEWARE`, de modo que las cabeceras `Access-Control-Allow-*` se agregan también a las respuestas de error (400, 401, 502) y los **preflight `OPTIONS` se responden antes de llegar a las vistas** (no requieren token).
- Métodos permitidos: `DELETE, GET, OPTIONS, PATCH, POST, PUT`. Cabeceras permitidas: `authorization` (token Bearer), `content-type` (JSON y multipart), `accept`, `accept-encoding`, `dnt`, `origin`, `user-agent`, `x-csrftoken`, `x-requested-with`. El preflight se cachea 24 h (`CORS_PREFLIGHT_MAX_AGE`).

Ejemplo de preflight respondido por la API:

```
OPTIONS /api/v1/products/ HTTP/1.1
Origin: https://mi-app.ejemplo.com
Access-Control-Request-Method: GET
Access-Control-Request-Headers: authorization

HTTP/1.1 200 OK
access-control-allow-origin: *
access-control-allow-methods: DELETE, GET, OPTIONS, PATCH, POST, PUT
access-control-allow-headers: accept, accept-encoding, authorization, content-type, ...
access-control-max-age: 86400
```

Variables de entorno:

| Variable | Default | Uso |
|---|---|---|
| `CORS_ALLOW_ALL_ORIGINS` | `True` | `*` para cualquier aplicación web, móvil o API. |
| `CORS_ALLOWED_ORIGINS` | vacío | Lista blanca separada por coma (`https://app1.com,https://app2.com`); se usa cuando `CORS_ALLOW_ALL_ORIGINS=False`. |
| `CORS_ALLOW_CREDENTIALS` | `False` | Activar solo si el cliente usa cookies o HTTP Basic; en ese caso se devuelve el origen exacto en lugar de `*`. |
| `CORS_PREFLIGHT_MAX_AGE` | `86400` | Segundos de caché del preflight. |

CORS es una restricción del navegador: sigue siendo obligatorio enviar `Authorization: Bearer <token>` en `/products/`, `/equipments/`, `/import/data-loads/` y `/import/logs/`.

## Colección Postman / Bruno

`postman/API-Avistidata-Chepita.postman_collection.json` contiene los 22 requests de la API (formato Postman Collection v2.1, importable también en Bruno con `Import Collection > Postman Collection`).

- Variables de colección: `base_url`, `token`, `expires_at`, `admin_email`, `admin_password`, `invalid_token`, `search`, `product_id`, `load_id`, `import_data_source`, `import_loaded_by` e `import_file_path`.
- `1. Autenticación`: login público (guarda automáticamente el token en `{{token}}`), login con credenciales inválidas (401) y logout protegido (limpia el token).
- `2. Catálogo (requieren token)`: `GET /products/` y `GET /equipments/`, con y sin filtros, más un caso de `product_id` no numérico (400). Las filas de query param deshabilitadas se activan con un clic para probar el filtro.
- `3. Importación (públicos - sin cambios)`: Excel, CSV y JSON tal como funcionaban antes, sin token.
- `4. Consultas de importación (requieren token)`: `data-loads`, `logs`, `logs?load_id=` y `load_id` no numérico (400).
- `5. Pruebas de seguridad (401 / token inválido)`: los cuatro GET protegidos sin header, token inexistente y esquema `Basic` en lugar de `Bearer`.
- Cada request incluye descripción (función, autenticación requerida, parámetros y respuestas esperadas) y un script de test que valida el status y la estructura `{success, message, data|errors}`.

Antes de usar la colección, ejecutar `1. Autenticación > Login (público)` y ajustar `{{import_file_path}}` con la ruta real del archivo a subir.

## Estructura

- `apps/authentication`: modelos de solo consulta (`admins`, `admin_tokens`), `AdminTokenAuthentication` (Bearer) y endpoints `login`/`logout` + comando `create_admin`.
- `apps/catalog`: modelos `products`/`equipments` y endpoints GET protegidos con filtros.
- `apps/imports/api`: serializers, views y rutas HTTP de importación; `list_views.py`/`list_serializers.py` contienen los GET protegidos de cargas y bitácora.
- `apps/imports/models.py`: modelos de solo consulta (`data_loads`, `procedure_execution_logs`, `managed = False`).
- `apps/imports/parsers`: lectura y transformación de Excel y CSV.
- `apps/imports/services`: serialización JSON y orquestación.
- `apps/imports/repositories`: acceso parametrizado a MySQL.
- `apps/imports/validators`: validaciones comunes y configurables.
- `config/settings.py`: settings desde `.env`, incluido el bloque CORS (`CORS_ALLOW_ALL_ORIGINS`, `CORS_ALLOWED_ORIGINS`, `CORS_PREFLIGHT_MAX_AGE`).

El flujo actual mantiene los registros en memoria como `list[dict]` y genera una sola cadena JSON antes de llamar al procedimiento. El servicio es el punto de extensión para añadir procesamiento por lotes si el volumen real lo requiere.
