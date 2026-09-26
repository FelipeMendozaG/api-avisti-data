"""Serializadores de solo lectura para los endpoints de consulta (GET) de importaciones."""

from rest_framework import serializers

from apps.imports.models import DataLoad, ProcedureExecutionLog


class DataLoadSerializer(serializers.ModelSerializer):
    class Meta:
        model = DataLoad
        fields = [
            "load_id",
            "data_source",
            "file_name",
            "load_date",
            "loaded_by",
            "processed_records",
            "load_status",
        ]


class ProcedureExecutionLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProcedureExecutionLog
        fields = [
            "log_id",
            "load_id",
            "procedure_name",
            "log_level",
            "step_description",
            "message",
            "created_at",
        ]