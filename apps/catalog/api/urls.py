from django.urls import path

from apps.catalog.api.views import EquipmentListView, ProductListView

urlpatterns = [
    path("products/", ProductListView.as_view(), name="product-list"),
    path("equipments/", EquipmentListView.as_view(), name="equipment-list"),
]