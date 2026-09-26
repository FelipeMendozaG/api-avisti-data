"""Paginación por número de página compartida por los endpoints de listado.

Mantiene el sobre estándar de la API (`success`, `message`, `data`) y añade un
objeto `pagination` con los metadatos de la página:

    {
      "success": true,
      "message": "Productos consultados correctamente",
      "data": [ ...registros de la página... ],
      "pagination": {
        "count": 8691,
        "page": 1,
        "page_size": 20,
        "total_pages": 435,
        "next": "http://host/api/v1/products/?page=2&page_size=20",
        "previous": null,
        "has_next": true,
        "has_previous": false
      }
    }

Parámetros de consulta: `?page=` (1-based) y `?page_size=` (1..PAGINATION_MAX_PAGE_SIZE,
`PAGINATION_DEFAULT_PAGE_SIZE` por defecto). Los filtros propios de cada endpoint
(por ejemplo `?search=` o `?product_id=`) se aplican **antes** de paginar, de modo
que `count` refleja el total filtrado.
"""

from django.conf import settings
from django.core.paginator import EmptyPage, Paginator
from rest_framework import status
from rest_framework.response import Response


class PaginationError(Exception):
    """Parámetros de paginación inválidos o página fuera de rango."""

    def __init__(self, message, errors, status_code=status.HTTP_400_BAD_REQUEST):
        super().__init__(message)
        self.message = message
        self.errors = errors
        self.status_code = status_code

    def as_response(self):
        return Response(
            {"success": False, "message": self.message, "errors": self.errors},
            status=self.status_code,
        )


def paginate(request, queryset, *, default_page_size=None, max_page_size=None):
    """Devuelve `(registros_de_la_pagina, metadatos)` para el queryset indicado.

    Lanza `PaginationError` si `page` o `page_size` no son enteros positivos, si
    `page_size` supera el máximo permitido (400) o si la página solicitada no
    existe en el queryset (404).
    """
    if default_page_size is None:
        default_page_size = getattr(settings, "PAGINATION_DEFAULT_PAGE_SIZE", 20)
    if max_page_size is None:
        max_page_size = getattr(settings, "PAGINATION_MAX_PAGE_SIZE", 100)

    page_number = _read_positive_int(request.query_params.get("page"), "page", default=1)
    page_size = _read_positive_int(request.query_params.get("page_size"), "page_size", default=default_page_size)
    if page_size > max_page_size:
        raise PaginationError("Parámetros de consulta inválidos", {"page_size": f"max_{max_page_size}"})

    paginator = Paginator(queryset, page_size)
    try:
        page = paginator.page(page_number)
    except EmptyPage:
        raise PaginationError(
            "Página fuera de rango",
            {"page": "out_of_range"},
            status.HTTP_404_NOT_FOUND,
        ) from None

    return list(page.object_list), {
        "count": paginator.count,
        "page": page.number,
        "page_size": paginator.per_page,
        "total_pages": paginator.num_pages if paginator.count else 0,
        "next": _page_link(request, page.next_page_number(), page_size) if page.has_next() else None,
        "previous": _page_link(request, page.previous_page_number(), page_size) if page.has_previous() else None,
        "has_next": page.has_next(),
        "has_previous": page.has_previous(),
    }


def _read_positive_int(raw_value, param_name, *, default):
    if raw_value in (None, ""):
        return default

    try:
        value = int(raw_value)
    except (TypeError, ValueError):
        raise PaginationError("Parámetros de consulta inválidos", {param_name: "invalid"}) from None

    if value < 1:
        raise PaginationError("Parámetros de consulta inválidos", {param_name: "invalid"})

    return value


def _page_link(request, page_number, page_size):
    """Enlace absoluto a otra página conservando los filtros de la petición actual."""
    query = request.query_params.copy()
    query["page"] = str(page_number)
    query["page_size"] = str(page_size)
    return f"{request.build_absolute_uri(request.path)}?{query.urlencode()}"
