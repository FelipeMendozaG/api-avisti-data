from django.db import models


class Product(models.Model):
    product_id = models.AutoField(primary_key=True)
    product_code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=150)
    url_image = models.TextField(null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    category = models.CharField(max_length=50)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "products"
        managed = False

    def __str__(self):
        return self.product_code


class Equipment(models.Model):
    equipment_id = models.AutoField(primary_key=True)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, db_column="product_id")
    load_id = models.IntegerField()
    serial_number = models.CharField(max_length=100, unique=True)
    acquisition_date = models.DateField()
    end_of_useful_life = models.DateField()
    current_market_value = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    life_cycle_status = models.CharField(max_length=30, default="IN_USE")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "equipments"
        managed = False

    def __str__(self):
        return self.serial_number