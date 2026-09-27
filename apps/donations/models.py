from django.db import models

from apps.authentication.models import Entity
from apps.catalog.models import Equipment


class DonationRequest(models.Model):
    request_id = models.AutoField(primary_key=True)
    entity = models.ForeignKey(Entity, on_delete=models.RESTRICT, db_column="entity_id")
    request_type = models.CharField(max_length=30)
    request_date = models.DateTimeField(auto_now_add=True)
    requested_quantity = models.IntegerField()
    need_description = models.TextField()
    request_status = models.CharField(max_length=30, default="ON_HOLD")

    class Meta:
        db_table = "donation_requests"
        managed = False

    def __str__(self):
        return f"{self.request_type}:{self.request_id}"


class DonationAssignment(models.Model):
    assignment_id = models.AutoField(primary_key=True)
    request = models.ForeignKey(DonationRequest, on_delete=models.RESTRICT, db_column="request_id")
    equipment = models.OneToOneField(Equipment, on_delete=models.RESTRICT, db_column="equipment_id")
    delivery_date = models.DateField()
    donation_deed_ref = models.CharField(max_length=100)
    estimated_beneficiaries_impact = models.IntegerField(default=0)

    class Meta:
        db_table = "donation_assignments"
        managed = False

    def __str__(self):
        return self.donation_deed_ref