from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from decimal import Decimal
from core.models import Business
from customers.models import Customer
from inventory.models import Brand, InventoryItem, StockTransaction

class ACUnit(models.Model):
    APPLIANCE_CHOICES = [
        ('AC', 'Air Conditioner (AC)'),
        ('REFRIGERATOR', 'Refrigerator / Fridge'),
        ('WASHING_MACHINE', 'Washing Machine'),
        ('COOLER', 'Air Cooler'),
    ]

    AC_TYPES = [
        ('Split AC', 'Split AC (Inverter / Non-Inverter)'),
        ('Window AC', 'Window AC'),
        ('Cassette AC', 'Cassette / Ceiling AC'),
        ('Multi-Split', 'Multi-Split AC System'),
        ('Tower AC', 'Tower / Floor Standing AC'),
        ('Ductable', 'Ductable Split AC'),
        ('Single Door', 'Single Door Refrigerator'),
        ('Double Door', 'Double Door / Frost-Free Refrigerator'),
        ('Deep Freezer', 'Deep Freezer / Chest Freezer'),
        ('Front Load', 'Front Load Washing Machine'),
        ('Top Load', 'Top Load Fully-Automatic Washing Machine'),
        ('Semi Auto', 'Semi-Automatic Twin Tub Washing Machine'),
        ('Desert Cooler', 'Desert Air Cooler'),
        ('Personal Cooler', 'Personal / Room Cooler'),
        ('Other Unit', 'Other Appliance'),
    ]

    CAPACITY_CHOICES = [
        ('0.75 Ton', '0.75 Ton'),
        ('1.0 Ton', '1.0 Ton'),
        ('1.5 Ton', '1.5 Ton'),
        ('2.0 Ton', '2.0 Ton'),
        ('2.5 Ton', '2.5 Ton'),
        ('3.0 Ton', '3.0 Ton'),
        ('4.0+ Ton', '4.0+ Ton (Commercial)'),
        ('180-220 Ltr', '180–220 Liters (Ref)'),
        ('250-350 Ltr', '250–350 Liters (Ref)'),
        ('400+ Ltr', '400+ Liters (Deep Freezer)'),
        ('6.0-7.5 Kg', '6.0–7.5 Kg (WM)'),
        ('8.0-10 Kg', '8.0–10 Kg (WM)'),
        ('40-60 Ltr', '40–60 Liters (Cooler)'),
        ('Standard', 'Standard Size'),
    ]

    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='ac_units')
    appliance_type = models.CharField(max_length=30, choices=APPLIANCE_CHOICES, default='AC')
    brand = models.ForeignKey(Brand, on_delete=models.SET_NULL, null=True, blank=True, related_name='ac_units')
    ac_type = models.CharField(max_length=40, choices=AC_TYPES, default='Split AC')
    capacity = models.CharField(max_length=30, choices=CAPACITY_CHOICES, default='1.5 Ton')
    model_number = models.CharField(max_length=100, blank=True)
    serial_number = models.CharField(max_length=100, blank=True)
    location_notes = models.CharField(max_length=150, blank=True, help_text="e.g. Kitchen, Master Bedroom, Balcony")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        brand_name = self.brand.name if self.brand else "Generic"
        return f"{self.get_appliance_type_display()}: {brand_name} {self.ac_type} ({self.capacity}) - {self.customer.name}"

class ServiceJob(models.Model):
    APPLIANCE_CHOICES = [
        ('AC', 'Air Conditioner (AC)'),
        ('REFRIGERATOR', 'Refrigerator / Fridge'),
        ('WASHING_MACHINE', 'Washing Machine'),
        ('COOLER', 'Air Cooler'),
    ]

    JOB_TYPE_CHOICES = [
        ('INSTALLATION', 'Installation (Wall mount/piping)'),
        ('UNINSTALLATION', 'Uninstallation / Shifting'),
        ('GENERAL_SERVICE', 'General Service / Maintenance (SVC only)'),
        ('REPAIR', 'Repair & Spare Part Replacement'),
        ('DEMO', 'Demo / Inspection'),
        ('REPEAT_COMPLAINT', 'Repeat Complaint / Warranty Rework'),
    ]

    STATUS_CHOICES = [
        ('NEW', 'New'),
        ('ASSIGNED', 'Assigned'),
        ('IN_PROGRESS', 'In Progress'),
        ('WAITING_FOR_PARTS', 'Waiting for Parts'),
        ('COMPLETED', 'Completed'),
        ('PAYMENT_PENDING', 'Payment Pending (Due)'),
        ('CLOSED', 'Closed'),
        ('CANCELLED', 'Cancelled / Aborted'),
    ]

    SERVICE_TYPE_CHOICES = [
        ('General Service', 'General Service / Cleaning (SVC only)'),
        ('Gas Charging', 'Refrigerant Leak & Gas Charging'),
        ('No Cooling', 'No Cooling / Poor Cooling'),
        ('Not Working', 'Not Working / Machine Dead'),
        ('Motor or PCB', 'Motor or PCB Failure'),
        ('Relay Overload', 'Relay / Overload Replacement'),
        ('Compressor Issue', 'Compressor Tripping / Replacement'),
        ('Capacitor Replacement', 'Capacitor Replacement / Motor Humming'),
        ('Drain & Gasket', 'Drain Pipe Blockage / Gasket Repair'),
        ('Water Leakage', 'Water Dripping / Leakage'),
        ('Installation', 'Installation / Wall Mount'),
        ('Uninstallation', 'Uninstallation'),
        ('Other Repair', 'Other Repair'),
    ]

    PAYMENT_STATUS_CHOICES = [
        ('PENDING', 'Due (Deuu)'),
        ('PAID', 'Paid'),
        ('WARRANTY', 'Warranty Claim (WTY)'),
    ]

    PAYMENT_METHOD_CHOICES = [
        ('CASH', 'Cash'),
        ('ESEWA', 'eSewa'),
        ('FONEPAY', 'Fonepay'),
        ('BANK', 'Bank Transfer'),
        ('DEALER_CLAIM', 'Dealer Claim Reimbursed'),
        ('OTHER', 'Other'),
    ]

    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name='service_jobs')
    job_number = models.CharField(max_length=30, unique=True, db_index=True)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='service_jobs')
    appliance_type = models.CharField(max_length=30, choices=APPLIANCE_CHOICES, default='AC', db_index=True)
    job_type = models.CharField(max_length=30, choices=JOB_TYPE_CHOICES, default='GENERAL_SERVICE', db_index=True)
    brand = models.ForeignKey(Brand, on_delete=models.SET_NULL, null=True, blank=True, related_name='service_jobs')
    ac_unit = models.ForeignKey(ACUnit, on_delete=models.SET_NULL, null=True, blank=True, related_name='service_jobs')
    
    # Quick snapshot fields in case unit record isn't fully linked
    ac_brand_name = models.CharField(max_length=80, blank=True)
    ac_type_name = models.CharField(max_length=50, blank=True, default="Split AC")
    ac_capacity_name = models.CharField(max_length=30, blank=True, default="1.5 Ton")

    service_type = models.CharField(max_length=60, choices=SERVICE_TYPE_CHOICES, default='No Cooling')
    complaint = models.TextField(help_text="Customer reported issue or inspection requirements")
    status = models.CharField(max_length=25, choices=STATUS_CHOICES, default='NEW', db_index=True)
    priority = models.CharField(max_length=20, default='NORMAL', choices=[('NORMAL', 'Normal'), ('URGENT', 'Urgent')])

    # Warranty / Dealer Tracking (Owner Excel Sheet WTY)
    is_warranty = models.BooleanField(default=False, db_index=True, help_text="True if work is covered under Brand / Dealer warranty (WTY)")
    warranty_dealer = models.ForeignKey('billing.Dealer', on_delete=models.SET_NULL, null=True, blank=True, related_name='warranty_jobs')
    dealer_claim_status = models.CharField(max_length=30, default='PENDING', choices=[
        ('PENDING', 'Pending Submission'),
        ('SUBMITTED', 'Submitted to Dealer'),
        ('SETTLED', 'Settled / Reimbursed'),
        ('REJECTED', 'Rejected'),
    ])
    dealer_claim_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))

    # Cancellation Tracking (Owner Excel Sheet 'Cancel Resion')
    cancel_reason = models.CharField(max_length=255, blank=True, help_text="e.g. 'He did not send him machine', 'Customer cancelled'")

    technician = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_jobs')
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='created_jobs')

    created_at = models.DateTimeField(default=timezone.now, db_index=True)
    start_time = models.DateTimeField(null=True, blank=True)
    completion_time = models.DateTimeField(null=True, blank=True)
    closed_at = models.DateTimeField(null=True, blank=True)

    technician_notes = models.TextField(blank=True)

    # Billing / Financials
    service_charge = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    parts_charge = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    discount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='PENDING')
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES, blank=True, default='CASH')
    payment_reference = models.CharField(max_length=100, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        wty_tag = " [WTY]" if self.is_warranty else ""
        return f"{self.job_number} - {self.customer.name} ({self.get_appliance_type_display()}){wty_tag}"

    @property
    def is_due(self):
        return not self.is_warranty and self.payment_status == 'PENDING' and self.status in ['COMPLETED', 'CLOSED', 'PAYMENT_PENDING']

    def recalculate_totals(self):
        parts_sum = self.parts_used.aggregate(
            total=models.Sum('subtotal')
        )['total'] or Decimal('0.00')
        self.parts_charge = parts_sum
        gross_total = (self.service_charge + self.parts_charge) - self.discount
        
        if self.is_warranty:
            self.dealer_claim_amount = max(Decimal('0.00'), gross_total)
            self.total_amount = Decimal('0.00')
            self.payment_status = 'WARRANTY'
            self.payment_method = 'DEALER_CLAIM'
        else:
            self.total_amount = max(Decimal('0.00'), gross_total)
            self.dealer_claim_amount = Decimal('0.00')
            
        self.save(update_fields=['parts_charge', 'total_amount', 'dealer_claim_amount', 'payment_status', 'payment_method'])

        # Auto-update or create linked Internal Invoice
        from billing.models import Invoice
        Invoice.sync_from_job(self)

    @classmethod
    def generate_next_job_number(cls, business=None):
        current_year = timezone.now().year
        prefix = f"JOB-{current_year}-"
        last_job = cls.objects.filter(job_number__startswith=prefix).order_by('-job_number').first()
        if last_job:
            try:
                seq = int(last_job.job_number.split('-')[-1]) + 1
            except ValueError:
                seq = 1
        else:
            count = cls.objects.count()
            seq = 480 + count if count < 10 else count + 1
        return f"JOB-{current_year}-{seq:05d}"

class WorkLog(models.Model):
    job = models.ForeignKey(ServiceJob, on_delete=models.CASCADE, related_name='work_logs')
    technician = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    description = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"{self.job.job_number}: {self.description}"

class JobPart(models.Model):
    job = models.ForeignKey(ServiceJob, on_delete=models.CASCADE, related_name='parts_used')
    inventory_item = models.ForeignKey(InventoryItem, on_delete=models.PROTECT, related_name='job_usages')
    quantity = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('1.00'))
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    added_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['added_at']

    def save(self, *args, **kwargs):
        self.subtotal = self.quantity * self.unit_price
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.inventory_item.part_name} x {self.quantity} on {self.job.job_number}"
