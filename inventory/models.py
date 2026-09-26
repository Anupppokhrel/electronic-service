from django.db import models
from django.contrib.auth.models import User
from decimal import Decimal
from core.models import Business

class Brand(models.Model):
    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name='brands')
    name = models.CharField(max_length=80)
    code = models.CharField(max_length=20, blank=True)
    is_common = models.BooleanField(default=False, help_text="True for generic/common parts usable across all brands")
    description = models.TextField(blank=True)
    website = models.URLField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']
        unique_together = ('business', 'name')

    def __str__(self):
        return self.name

    @property
    def total_inventory_items(self):
        return self.inventory_items.count()

    @property
    def total_jobs_count(self):
        # Direct relationship to service jobs
        return self.service_jobs.count()

class Category(models.Model):
    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name='categories')
    name = models.CharField(max_length=80)
    description = models.CharField(max_length=255, blank=True)

    class Meta:
        verbose_name_plural = "Categories"
        ordering = ['name']

    def __str__(self):
        return self.name

class InventoryItem(models.Model):
    INVENTORY_TYPES = [
        ('BRAND_SPECIFIC', 'Brand Specific'),
        ('COMMON', 'Common Inventory'),
    ]

    UNIT_CHOICES = [
        ('pcs', 'Pieces (pcs)'),
        ('meter', 'Meters (m)'),
        ('kg', 'Kilograms (kg)'),
        ('set', 'Sets (set)'),
        ('can', 'Cans (can)'),
        ('roll', 'Rolls (roll)'),
    ]

    APPLIANCE_CHOICES = [
        ('ALL', 'All / Common Appliances'),
        ('AC', 'Air Conditioner (AC)'),
        ('REFRIGERATOR', 'Refrigerator / Fridge'),
        ('WASHING_MACHINE', 'Washing Machine'),
        ('COOLER', 'Air Cooler'),
    ]

    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name='inventory_items')
    part_name = models.CharField(max_length=150)
    appliance_type = models.CharField(max_length=30, choices=APPLIANCE_CHOICES, default='ALL', db_index=True)
    part_code = models.CharField(max_length=50, blank=True)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True, related_name='items')
    inventory_type = models.CharField(max_length=20, choices=INVENTORY_TYPES, default='BRAND_SPECIFIC')
    brand = models.ForeignKey(Brand, on_delete=models.SET_NULL, null=True, blank=True, related_name='inventory_items')
    quantity = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    minimum_stock = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('2.00'))
    unit = models.CharField(max_length=15, choices=UNIT_CHOICES, default='pcs')
    purchase_price = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    selling_price = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    supplier = models.CharField(max_length=150, blank=True)
    storage_bin = models.CharField(max_length=50, blank=True, help_text="Rack / Shelf location")
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['part_name']

    def __str__(self):
        return f"{self.part_name} ({self.get_unit_display()})"

    @property
    def is_low_stock(self):
        return self.quantity <= self.minimum_stock

    @property
    def stock_display(self):
        # Format cleanly: if integer e.g. 4.00 -> 4, else 4.5
        if self.quantity % 1 == 0:
            return f"{int(self.quantity)} {self.unit}"
        return f"{self.quantity} {self.unit}"

    @property
    def min_stock_display(self):
        if self.minimum_stock % 1 == 0:
            return f"{int(self.minimum_stock)} {self.unit}"
        return f"{self.minimum_stock} {self.unit}"

class StockTransaction(models.Model):
    TRANSACTION_TYPES = [
        ('PURCHASE', 'Purchase / Restock'),
        ('SERVICE_USAGE', 'Used in Service Job'),
        ('RETURN', 'Job Part Returned / Reversal'),
        ('ADJUSTMENT', 'Manual Adjustment / Audit'),
    ]

    item = models.ForeignKey(InventoryItem, on_delete=models.CASCADE, related_name='transactions')
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    quantity_change = models.DecimalField(max_digits=10, decimal_places=2) # Negative for usage, positive for restock
    balance_after = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    service_job = models.ForeignKey('services.ServiceJob', on_delete=models.SET_NULL, null=True, blank=True, related_name='stock_transactions')
    job_reference = models.CharField(max_length=50, blank=True)
    performed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    notes = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.get_transaction_type_display()} - {self.item.part_name} ({self.quantity_change})"
