from rest_framework import serializers

from apps.catalog.models import Equipment, Product


class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = ["product_id", "product_code", "name", "url_image", "description", "category", "created_at"]


class EquipmentSerializer(serializers.ModelSerializer):
    product_id = serializers.IntegerField(read_only=True)
    product_code = serializers.CharField(source="product.product_code", read_only=True, allow_null=True)

    class Meta:
        model = Equipment
        fields = [
            "equipment_id",
            "product_id",
            "product_code",
            "load_id",
            "serial_number",
            "acquisition_date",
            "end_of_useful_life",
            "current_market_value",
            "life_cycle_status",
            "created_at",
            "updated_at",
        ]