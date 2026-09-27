from django.db import models


class Admin(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=100, null=True, blank=True)
    email = models.EmailField(max_length=150, unique=True)
    password = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "admins"
        managed = False

    @property
    def is_authenticated(self):
        """Requerido por `IsAuthenticated` de DRF: un Admin es un usuario autenticado."""
        return True

    def __str__(self):
        return self.email


class AdminToken(models.Model):
    token_id = models.AutoField(primary_key=True)
    admin = models.ForeignKey(Admin, on_delete=models.CASCADE, db_column="admin_id")
    token = models.CharField(max_length=64, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    class Meta:
        db_table = "admin_tokens"
        managed = False

    def __str__(self):
        return self.token


class User(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=100, null=True, blank=True)
    email = models.EmailField(max_length=150, unique=True)
    password = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "users"
        managed = False

    def __str__(self):
        return self.email


class Entity(models.Model):
    entity_id = models.AutoField(primary_key=True)
    tax_id = models.CharField(max_length=20, unique=True)
    company_name = models.CharField(max_length=150)
    entity_type = models.CharField(max_length=50)
    address = models.CharField(max_length=200)
    contact_name = models.CharField(max_length=100)
    contact_email = models.EmailField(max_length=100)
    contact_phone = models.CharField(max_length=20, null=True, blank=True)
    verification_status = models.CharField(max_length=20, default="PENDING")
    registration_date = models.DateTimeField(auto_now_add=True)
    user = models.OneToOneField(User, on_delete=models.CASCADE, db_column="user_id")

    class Meta:
        db_table = "entities"
        managed = False

    def __str__(self):
        return self.company_name
