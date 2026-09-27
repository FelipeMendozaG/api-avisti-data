from datetime import date

from django.db import IntegrityError, transaction
from django.db.models import OuterRef, Prefetch, Q, Subquery
from django.utils.dateparse import parse_date
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.authentication.authentication import AdminTokenAuthentication
from apps.authentication.models import Entity
from apps.catalog.models import Equipment, TechnicalEvaluation
from apps.donations.api.serializers import (
    AvailableEquipmentSerializer,
    DonationAssignmentCreateSerializer,
    DonationAssignmentSerializer,
    DonationRequestSerializer,
    DonationRequestStatusSerializer,
    EntitySerializer,
    EntityVerificationSerializer,
)
from apps.donations.models import DonationAssignment, DonationRequest
from apps.pagination import PaginationError, paginate

FAVORABLE_VERDICTS = ["SUITABLE_FOR_DONATION", "SUITABLE_FOR_AGREEMENT"]
REQUEST_STATUSES = ("ON_HOLD", "APPROVED", "REJECTED", "DELIVERED")
EQUIPMENT_STATUSES = ('DEPRECIATED', 'UNDER_EVALUATION')


def success(message, data, http_status=status.HTTP_200_OK, **extra):
    return Response({"status": "success", "success": True, "message": message, "data": data, **extra}, status=http_status)


def failure(message, errors, http_status=status.HTTP_400_BAD_REQUEST):
    return Response({"status": "error", "success": False, "message": message, "errors": errors}, status=http_status)


class AdminAPIView(APIView):
    authentication_classes = [AdminTokenAuthentication]
    permission_classes = [IsAuthenticated]


class EntityListView(AdminAPIView):
    def get(self, request):
        queryset = Entity.objects.all().order_by("entity_id")
        verification_status = request.query_params.get("verification_status")
        if verification_status:
            if verification_status not in {"PENDING", "VERIFIED", "REJECTED"}:
                return failure("Parámetros de consulta inválidos", {"verification_status": "invalid"})
            queryset = queryset.filter(verification_status=verification_status)

        search = request.query_params.get("search")
        if search:
            queryset = queryset.filter(Q(tax_id__icontains=search) | Q(company_name__icontains=search))

        try:
            entities, pagination = paginate(request, queryset)
        except PaginationError as exc:
            return exc.as_response()
        return success("Entidades consultadas correctamente", EntitySerializer(entities, many=True).data, pagination=pagination)


class EntityVerificationView(AdminAPIView):
    def patch(self, request, entity_id):
        serializer = EntityVerificationSerializer(data=request.data)
        if not serializer.is_valid():
            return failure("Datos inválidos", serializer.errors)
        entity = Entity.objects.filter(entity_id=entity_id).first()
        if entity is None:
            return failure("Entidad no encontrada", {"entity_id": "not_found"}, status.HTTP_404_NOT_FOUND)
        entity.verification_status = serializer.validated_data["verification_status"]
        entity.save(update_fields=["verification_status"])
        return success("Estado de entidad actualizado correctamente", EntitySerializer(entity).data)


class DonationRequestListView(AdminAPIView):
    def get(self, request):
        queryset = DonationRequest.objects.select_related("entity").all().order_by("-request_date")
        for field, choices in (("request_status", REQUEST_STATUSES), ("request_type", None)):
            value = request.query_params.get(field)
            if value:
                if choices and value not in choices:
                    return failure("Parámetros de consulta inválidos", {field: "invalid"})
                queryset = queryset.filter(**{field: value})

        for parameter, lookup in (("date_from", "request_date__date__gte"), ("date_to", "request_date__date__lte")):
            raw_value = request.query_params.get(parameter)
            if raw_value:
                parsed = parse_date(raw_value)
                if parsed is None:
                    return failure("Parámetros de consulta inválidos", {parameter: "invalid"})
                queryset = queryset.filter(**{lookup: parsed})

        try:
            requests, pagination = paginate(request, queryset)
        except PaginationError as exc:
            return exc.as_response()
        return success("Solicitudes consultadas correctamente", DonationRequestSerializer(requests, many=True).data, pagination=pagination)


class DonationRequestDetailView(AdminAPIView):
    def get(self, request, request_id):
        donation_request = (
            DonationRequest.objects.select_related("entity")
            .prefetch_related("donationassignment_set__equipment")
            .filter(request_id=request_id)
            .first()
        )
        if donation_request is None:
            return failure("Solicitud no encontrada", {"request_id": "not_found"}, status.HTTP_404_NOT_FOUND)
        return success("Solicitud consultada correctamente", DonationRequestSerializer(donation_request).data)


class DonationRequestStatusView(AdminAPIView):
    def patch(self, request, request_id):
        serializer = DonationRequestStatusSerializer(data=request.data)
        if not serializer.is_valid():
            return failure("Datos inválidos", serializer.errors)
        donation_request = DonationRequest.objects.filter(request_id=request_id).first()
        if donation_request is None:
            return failure("Solicitud no encontrada", {"request_id": "not_found"}, status.HTTP_404_NOT_FOUND)
        donation_request.request_status = serializer.validated_data["request_status"]
        donation_request.save(update_fields=["request_status"])
        return success("Estado de solicitud actualizado correctamente", DonationRequestSerializer(donation_request).data)


class AvailableEquipmentView(AdminAPIView):
    def get(self, request):
        latest_evaluation_id = Subquery(
            TechnicalEvaluation.objects.filter(equipment_id=OuterRef("pk"))
            .order_by("-evaluation_date", "-evaluation_id")
            .values("evaluation_id")[:1]
        )
        evaluations = TechnicalEvaluation.objects.filter(
            is_operational=True,
            final_verdict__in=FAVORABLE_VERDICTS,
        ).order_by("-evaluation_date")
        product_query = request.query_params.get("product_query")
        queryset = (
            Equipment.objects.select_related("product")
            .prefetch_related(Prefetch("technicalevaluation_set", queryset=evaluations, to_attr="eligible_evaluations"))
            .filter(
                life_cycle_status__in=EQUIPMENT_STATUSES,
                donationassignment__isnull=True,
                technicalevaluation__evaluation_id=latest_evaluation_id,
                technicalevaluation__is_operational=True,
                technicalevaluation__final_verdict__in=FAVORABLE_VERDICTS,
            )
            .distinct()
            .order_by("equipment_id")
        )
        if product_query:
            queryset = queryset.filter(
                Q(product__name__icontains=product_query)
                | Q(product__product_code__icontains=product_query)
                | Q(serial_number__icontains=product_query)
            )
        try:
            equipments, pagination = paginate(request, queryset)
        except PaginationError as exc:
            return exc.as_response()
        return success("Equipos disponibles consultados correctamente", AvailableEquipmentSerializer(equipments, many=True).data, pagination=pagination)


class DonationAssignmentCreateView(AdminAPIView):
    def post(self, request):
        serializer = DonationAssignmentCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return failure("Datos inválidos", serializer.errors)
        values = serializer.validated_data
        try:
            with transaction.atomic():
                donation_request = DonationRequest.objects.select_for_update().get(request_id=values["request_id"])
                if donation_request.request_status != "APPROVED":
                    return failure("La solicitud no está aprobada", {"request_status": "must_be_approved"}, status.HTTP_409_CONFLICT)

                equipment = Equipment.objects.select_for_update().get(equipment_id=values["equipment_id"])
                if equipment.life_cycle_status not in EQUIPMENT_STATUSES:
                    return failure("El equipo no está disponible para donación", {"equipment_id": "unavailable"}, status.HTTP_409_CONFLICT)
                if DonationAssignment.objects.filter(equipment_id=equipment.equipment_id).exists():
                    return failure("El equipo ya está asignado", {"equipment_id": "already_assigned"}, status.HTTP_409_CONFLICT)
                latest_evaluation = TechnicalEvaluation.objects.filter(
                    equipment_id=equipment.equipment_id,
                ).order_by("-evaluation_date", "-evaluation_id").first()
                if latest_evaluation is None or not latest_evaluation.is_operational or latest_evaluation.final_verdict not in FAVORABLE_VERDICTS:
                    return failure("El equipo no tiene evaluación técnica favorable", {"equipment_id": "technical_evaluation_required"}, status.HTTP_409_CONFLICT)

                assignment = DonationAssignment.objects.create(
                    request=donation_request,
                    equipment=equipment,
                    delivery_date=values["delivery_date"],
                    donation_deed_ref=values["donation_deed_ref"],
                    estimated_beneficiaries_impact=values["estimated_beneficiaries_impact"],
                )
                Equipment.objects.filter(equipment_id=equipment.equipment_id).update(life_cycle_status="ASSIGNED")
                assignments_count = DonationAssignment.objects.filter(request_id=donation_request.request_id).count()
                if assignments_count >= donation_request.requested_quantity:
                    DonationRequest.objects.filter(request_id=donation_request.request_id).update(request_status="DELIVERED")
        except DonationRequest.DoesNotExist:
            return failure("Solicitud no encontrada", {"request_id": "not_found"}, status.HTTP_404_NOT_FOUND)
        except Equipment.DoesNotExist:
            return failure("Equipo no encontrado", {"equipment_id": "not_found"}, status.HTTP_404_NOT_FOUND)
        except IntegrityError:
            return failure("El equipo ya está asignado", {"equipment_id": "already_assigned"}, status.HTTP_409_CONFLICT)

        return success("Asignación registrada correctamente", DonationAssignmentSerializer(assignment).data, status.HTTP_201_CREATED)


class DonationAssignmentDeleteView(AdminAPIView):
    def delete(self, request, assignment_id):
        try:
            with transaction.atomic():
                assignment = DonationAssignment.objects.select_for_update().select_related("equipment", "request").get(assignment_id=assignment_id)
                equipment = Equipment.objects.select_for_update().get(equipment_id=assignment.equipment_id)
                donation_request = DonationRequest.objects.select_for_update().get(request_id=assignment.request_id)
                assignment.delete()
                restored_status = "AVAILABLE" if equipment.end_of_useful_life >= date.today() else "DEPRECIATED"
                Equipment.objects.filter(equipment_id=equipment.equipment_id).update(life_cycle_status=restored_status)
                if donation_request.request_status == "DELIVERED":
                    DonationRequest.objects.filter(request_id=donation_request.request_id).update(request_status="APPROVED")
        except DonationAssignment.DoesNotExist:
            return failure("Asignación no encontrada", {"assignment_id": "not_found"}, status.HTTP_404_NOT_FOUND)
        except Equipment.DoesNotExist:
            return failure("Equipo no encontrado", {"equipment_id": "not_found"}, status.HTTP_404_NOT_FOUND)
        except DonationRequest.DoesNotExist:
            return failure("Solicitud no encontrada", {"request_id": "not_found"}, status.HTTP_404_NOT_FOUND)
        return success("Asignación cancelada correctamente", None)