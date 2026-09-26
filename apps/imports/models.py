from django.db import models


class DataLoad(models.Model):
    load_id = models.AutoField(primary_key=True)
    data_source = models.CharField(max_length=50)
    file_name = models.CharField(max_length=255, null=True, blank=True)
    load_date = models.DateTimeField(auto_now_add=True)
    loaded_by = models.CharField(max_length=50)
    processed_records = models.IntegerField(default=0)
    load_status = models.CharField(max_length=20, default="PENDING")

    class Meta:
        db_table = "data_loads"
        managed = False

    def __str__(self):
        return f"{self.data_source}:{self.load_id}"


class ProcedureExecutionLog(models.Model):
    log_id = models.AutoField(primary_key=True)
    load_id = models.IntegerField(null=True, blank=True)
    procedure_name = models.CharField(max_length=100, default="sp_importar_excel")
    log_level = models.CharField(max_length=20, null=True, blank=True)
    step_description = models.CharField(max_length=255, null=True, blank=True)
    message = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "procedure_execution_logs"
        managed = False

    def __str__(self):
        return f"{self.procedure_name}:{self.log_id}"