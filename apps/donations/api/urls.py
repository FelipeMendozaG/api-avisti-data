from django.urls import path

from apps.donations.api.views import (
    AvailableEquipmentView,
    DonationAssignmentCreateView,
    DonationAssignmentDeleteView,
    DonationRequestDetailView,
    DonationRequestListView,
    DonationRequestStatusView,
    EntityListView,
    EntityVerificationView,
)

urlpatterns = [
    path("entities", EntityListView.as_view(), name="admin-entity-list"),
    path("entities/<int:entity_id>/verification", EntityVerificationView.as_view(), name="admin-entity-verification"),
    path("donation-requests", DonationRequestListView.as_view(), name="admin-donation-request-list"),
    path("donation-requests/<int:request_id>", DonationRequestDetailView.as_view(), name="admin-donation-request-detail"),
    path("donation-requests/<int:request_id>/status", DonationRequestStatusView.as_view(), name="admin-donation-request-status"),
    path("equipments/available-for-donation", AvailableEquipmentView.as_view(), name="admin-available-equipment-list"),
    path("donation-assignments", DonationAssignmentCreateView.as_view(), name="admin-donation-assignment-create"),
    path("donation-assignments/<int:assignment_id>", DonationAssignmentDeleteView.as_view(), name="admin-donation-assignment-delete"),
]