from rest_framework import serializers

from apps.authentication.models import Entity
from apps.catalog.models import Equipment, TechnicalEvaluation
from apps.donations.models import DonationAssignment, DonationRequest


class EntitySerializer(serializers.ModelSerializer):
    class Meta:
        model = Entity
        fields = [
            "entity_id",
            "tax_id",
            "company_name",
            "entity_type",
            "address",
            "contact_name",
            "contact_email",
            "contact_phone",
            "verification_status",
            "registration_date",
        ]


class EntityVerificationSerializer(serializers.Serializer):
    verification_status = serializers.ChoiceField(choices=["PENDING", "VERIFIED", "REJECTED"])


class TechnicalEvaluationSerializer(serializers.ModelSerializer):
    class Meta:
        model = TechnicalEvaluation
        fields = [
            "evaluation_id",
            "evaluation_date",
            "reusability_score",
            "is_operational",
            "requires_refurbishment",
            "final_verdict",
            "remarks",
        ]


class AvailableEquipmentSerializer(serializers.ModelSerializer):
    product_code = serializers.CharField(source="product.product_code", read_only=True)
    product_name = serializers.CharField(source="product.name", read_only=True)
    technical_evaluation = serializers.SerializerMethodField()

    class Meta:
        model = Equipment
        fields = [
            "equipment_id",
            "product_id",
            "product_code",
            "product_name",
            "serial_number",
            "acquisition_date",
            "end_of_useful_life",
            "current_market_value",
            "life_cycle_status",
            "technical_evaluation",
        ]

    def get_technical_evaluation(self, obj):
        evaluations = getattr(obj, "eligible_evaluations", [])
        evaluation = evaluations[0] if evaluations else None
        return TechnicalEvaluationSerializer(evaluation).data if evaluation else None


class DonationAssignmentSerializer(serializers.ModelSerializer):
    equipment_id = serializers.IntegerField(source="equipment.equipment_id", read_only=True)

    class Meta:
        model = DonationAssignment
        fields = [
            "assignment_id",
            "request_id",
            "equipment_id",
            "delivery_date",
            "donation_deed_ref",
            "estimated_beneficiaries_impact",
        ]


class DonationRequestSerializer(serializers.ModelSerializer):
    entity = EntitySerializer(read_only=True)
    assignments = DonationAssignmentSerializer(source="donationassignment_set", many=True, read_only=True)

    class Meta:
        model = DonationRequest
        fields = [
            "request_id",
            "entity",
            "request_type",
            "request_date",
            "requested_quantity",
            "need_description",
            "request_status",
            "assignments",
        ]


class DonationRequestStatusSerializer(serializers.Serializer):
    request_status = serializers.ChoiceField(choices=["APPROVED", "REJECTED"])


class DonationAssignmentCreateSerializer(serializers.Serializer):
    request_id = serializers.IntegerField(min_value=1)
    equipment_id = serializers.IntegerField(min_value=1)
    delivery_date = serializers.DateField()
    donation_deed_ref = serializers.CharField(max_length=100, allow_blank=False, trim_whitespace=True)
    estimated_beneficiaries_impact = serializers.IntegerField(min_value=0)