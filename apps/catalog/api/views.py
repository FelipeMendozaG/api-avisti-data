from django.db.models import Q
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.authentication.authentication import AdminTokenAuthentication
from apps.catalog.api.serializers import EquipmentSerializer, ProductSerializer
from apps.catalog.models import Equipment, Product
from apps.pagination import PaginationError, paginate


class ProductListView(APIView):
    """GET /api/v1/products/ — requiere token Bearer. Filtro `?search=` y paginación `?page=&page_size=`."""

    authentication_classes = [AdminTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        queryset = Product.objects.all().order_by("product_id")
        search = request.query_params.get("search")
        if search:
            queryset = queryset.filter(
                Q(product_code__icontains=search) | Q(name__icontains=search) | Q(description__icontains=search)
            )

        try:
            products, pagination = paginate(request, queryset)
        except PaginationError as exc:
            return exc.as_response()

        serializer = ProductSerializer(products, many=True)
        return Response(
            {
                "success": True,
                "message": "Productos consultados correctamente",
                "data": serializer.data,
                "pagination": pagination,
            }
        )


class EquipmentListView(APIView):
    """GET /api/v1/equipments/ — requiere token Bearer. Filtro `?product_id=` y paginación `?page=&page_size=`."""

    authentication_classes = [AdminTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        product_id = request.query_params.get("product_id")
        product_id_value = None
        if product_id not in (None, ""):
            try:
                product_id_value = int(product_id)
            except (TypeError, ValueError):
                return Response(
                    {
                        "success": False,
                        "message": "Parámetros de consulta inválidos",
                        "errors": {"product_id": "invalid"},
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

        queryset = Equipment.objects.select_related("product").all().order_by("equipment_id")
        if product_id_value is not None:
            queryset = queryset.filter(product_id=product_id_value)

        try:
            equipments, pagination = paginate(request, queryset)
        except PaginationError as exc:
            return exc.as_response()

        serializer = EquipmentSerializer(equipments, many=True)
        return Response(
            {
                "success": True,
                "message": "Equipos consultados correctamente",
                "data": serializer.data,
                "pagination": pagination,
            }
        )