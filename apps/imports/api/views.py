import logging

from rest_framework import status
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.imports.api.serializers import JSONImportSerializer
from apps.imports.exceptions import ImportRepositoryError, ImportValidationError
from apps.imports.parsers.csv_parser import CSVParser
from apps.imports.parsers.excel_parser import ExcelParser
from apps.imports.repositories.import_repository import ImportRepository
from apps.imports.services.import_service import ImportService

logger = logging.getLogger(__name__)


class FileImportView(APIView):
    parser_classes = [MultiPartParser, FormParser]
    source = None
    parser_class = None

    def handle_exception(self, exc):
        response = super().handle_exception(exc)
        if response is None:
            return response
        return Response(
            {"success": False, "message": "No se pudo procesar la información", "errors": {"request": response.data}},
            status=response.status_code,
            headers=response.headers,
        )

    def post(self, request):
        try:
            records = self.parser_class().parse(request.FILES.get("file"))
            data = ImportService(ImportRepository()).process(records, self.source)
            return Response({"success": True, "message": "Información procesada correctamente", "data": data})
        except ImportValidationError as exc:
            return Response(
                {"success": False, "message": exc.message, "errors": exc.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except ImportRepositoryError:
            logger.exception("Stored procedure failed for source=%s", self.source)
            return Response(
                {"success": False, "message": "No se pudo procesar la información", "errors": {"database": "processing_error"}},
                status=status.HTTP_502_BAD_GATEWAY,
            )


class ExcelImportView(FileImportView):
    source = "excel"
    parser_class = ExcelParser

    def post(self, request):
        uploaded_file = request.FILES.get("file")
        data_source = request.data.get("data_source")
        loaded_by = request.data.get("loaded_by")
        if not data_source or not loaded_by:
            return Response(
                {
                    "success": False,
                    "message": "No se pudo procesar la información",
                    "errors": {"data_source": "required", "loaded_by": "required"},
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            records = self.parser_class().parse(uploaded_file)
            data = ImportService(ImportRepository()).process_excel(
                records,
                data_source=data_source,
                file_name=uploaded_file.name,
                loaded_by=loaded_by,
            )
            return Response({"success": True, "message": "Información procesada correctamente", "data": data})
        except ImportValidationError as exc:
            return Response(
                {"success": False, "message": exc.message, "errors": exc.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except ImportRepositoryError:
            logger.exception("Stored procedure failed for source=excel")
            return Response(
                {"success": False, "message": "No se pudo procesar la información", "errors": {"database": "processing_error"}},
                status=status.HTTP_502_BAD_GATEWAY,
            )


class CSVImportView(FileImportView):
    source = "csv"
    parser_class = CSVParser


class JSONImportView(APIView):
    parser_classes = [JSONParser]

    def handle_exception(self, exc):
        response = super().handle_exception(exc)
        if response is None:
            return response
        return Response(
            {"success": False, "message": "No se pudo procesar la información", "errors": {"request": response.data}},
            status=response.status_code,
            headers=response.headers,
        )

    def post(self, request):
        serializer = JSONImportSerializer(data={"records": request.data})
        if not serializer.is_valid():
            return Response(
                {"success": False, "message": "No se pudo procesar la información", "errors": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            data = ImportService(ImportRepository()).process(serializer.validated_data["records"], "json")
            return Response({"success": True, "message": "Información procesada correctamente", "data": data})
        except ImportRepositoryError:
            logger.exception("Stored procedure failed for source=json")
            return Response(
                {"success": False, "message": "No se pudo procesar la información", "errors": {"database": "processing_error"}},
                status=status.HTTP_502_BAD_GATEWAY,
            )