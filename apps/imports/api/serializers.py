from rest_framework import serializers


class RecordSerializer(serializers.Serializer):
    values = serializers.DictField(child=serializers.JSONField(allow_null=True))


class JSONImportSerializer(serializers.Serializer):
    records = serializers.JSONField()

    def validate_records(self, value):
        records = value if isinstance(value, list) else [value]
        if not records or not all(isinstance(record, dict) for record in records):
            raise serializers.ValidationError("Debe enviar un objeto o una lista de objetos.")

        validated_records = []
        for record in records:
            serializer = RecordSerializer(data={"values": record})
            serializer.is_valid(raise_exception=True)
            validated_records.append(serializer.validated_data["values"])
        return validated_records