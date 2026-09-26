"""Endpoints de consulta (GET) de importaciones. No modifican el flujo de importación existente."""

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.authentication.authentication import AdminTokenAuthentication
from apps.imports.api.list_serializers import DataLoadSerializer, ProcedureExecutionLogSerializer
from apps.imports.models import DataLoad, ProcedureExecutionLog
from apps.pagination import PaginationError, paginate


class DataLoadListView(APIView):
    """GET /api/v1/import/data-loads/ — requiere token Bearer. Paginación `?page=&page_size=`."""

    authentication_classes = [AdminTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        queryset = DataLoad.objects.all().order_by("-load_date")

        try:
            data_loads, pagination = paginate(request, queryset)
        except PaginationError as exc:
            return exc.as_response()

        serializer = DataLoadSerializer(data_loads, many=True)
        return Response(
            {
                "success": True,
                "message": "Cargas de datos consultadas correctamente",
                "data": serializer.data,
                "pagination": pagination,
            }
        )


class ProcedureExecutionLogListView(APIView):
    """GET /api/v1/import/logs/ — requiere token Bearer. Filtro opcional `?load_id=`."""

    authentication_classes = [AdminTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        load_id = request.query_params.get("load_id")
        load_id_value = None
        if load_id not in (None, ""):
            try:
                load_id_value = int(load_id)
            except (TypeError, ValueError):
                return Response(
                    {
                        "success": False,
                        "message": "Parámetros de consulta inválidos",
                        "errors": {"load_id": "invalid"},
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

        queryset = ProcedureExecutionLog.objects.all().order_by("-created_at")
        if load_id_value is not None:
            queryset = queryset.filter(load_id=load_id_value)

        serializer = ProcedureExecutionLogSerializer(queryset, many=True)
        return Response(
            {
                "success": True,
                "message": "Bitácora de ejecución consultada correctamente",
                "data": serializer.data,
            }
        )