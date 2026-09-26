from django.db import models
from django.contrib.auth.models import User
from decimal import Decimal
from django.utils import timezone
from core.models import Business
from customers.models import Customer
from inventory.models import Brand

class Dealer(models.Model):
    """
    Authorized Brand Dealers, Distributors and Showrooms that authorize
    warranty repairs and reimburse the workshop (e.g. LG Showroom Damak, Samsung Plaza).
    """
    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name='dealers')
    name = models.CharField(max_length=150)
    brand = models.ForeignKey(Brand, on_delete=models.SET_NULL, null=True, blank=True, related_name='dealers')
    contact_person = models.CharField(max_length=100, blank=True)
    phone = models.CharField(max_length=30, blank=True)
    address = models.CharField(max_length=200, blank=True, default="Damak, Jhapa")
    notes = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        brand_name = f" [{self.brand.name}]" if self.brand else ""
        return f"{self.name}{brand_name}"

    @property
    def pending_claims_count(self):
        return self.warranty_jobs.filter(dealer_claim_status__in=['PENDING', 'SUBMITTED']).count()

    @property
    def total_claim_amount(self):
        return self.warranty_jobs.aggregate(total=models.Sum('dealer_claim_amount'))['total'] or Decimal('0.00')

    @property
    def settled_claim_amount(self):
        return self.warranty_jobs.filter(dealer_claim_status='SETTLED').aggregate(total=models.Sum('dealer_claim_amount'))['total'] or Decimal('0.00')


class Invoice(models.Model):
    DEALER_CLAIM_STATUSES = [
        ('PENDING', 'Pending Submission'),
        ('SUBMITTED', 'Submitted to Dealer'),
        ('SETTLED', 'Settled / Reimbursed'),
        ('REJECTED', 'Rejected'),
    ]

    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name='invoices')
    invoice_number = models.CharField(max_length=35, unique=True, db_index=True)
    job = models.OneToOneField('services.ServiceJob', on_delete=models.CASCADE, related_name='invoice')
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='invoices')
    technician = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='invoices')
    
    ac_brand = models.CharField(max_length=80, blank=True)
    service_description = models.CharField(max_length=200, blank=True)
    
    service_charge = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    parts_charge = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    discount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))

    # Warranty / Dealer Billing Tracking
    is_warranty = models.BooleanField(default=False, db_index=True)
    dealer = models.ForeignKey(Dealer, on_delete=models.SET_NULL, null=True, blank=True, related_name='invoices')
    dealer_claim_status = models.CharField(max_length=30, default='PENDING', choices=DEALER_CLAIM_STATUSES)
    dealer_claim_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))

    payment_status = models.CharField(max_length=20, default='PENDING', choices=[
        ('PENDING', 'Due (Deuu)'),
        ('PAID', 'Paid'),
        ('WARRANTY', 'Warranty Claim (WTY)'),
    ])
    payment_method = models.CharField(max_length=20, blank=True, default='CASH', choices=[
        ('CASH', 'Cash'),
        ('ESEWA', 'eSewa'),
        ('FONEPAY', 'Fonepay'),
        ('BANK', 'Bank Transfer'),
        ('DEALER_CLAIM', 'Dealer Claim Reimbursed'),
        ('OTHER', 'Other'),
    ])
    paid_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True, default="Internal Workshop Billing Record")
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        if self.is_warranty:
            return f"{self.invoice_number} (WTY - Claim Rs. {self.dealer_claim_amount})"
        return f"{self.invoice_number} ({self.job.job_number}) - Rs. {self.total_amount}"

    @property
    def amount_due(self):
        if self.is_warranty:
            return Decimal('0.00')
        return max(Decimal('0.00'), self.total_amount - self.amount_paid)

    @property
    def is_due(self):
        return not self.is_warranty and self.payment_status == 'PENDING' and self.amount_due > Decimal('0.00')

    @classmethod
    def sync_from_job(cls, job):
        inv_num = job.job_number.replace('JOB-', 'INV-')
        brand_name = job.ac_brand_name
        if not brand_name and job.brand:
            brand_name = job.brand.name
        elif not brand_name and job.ac_unit and job.ac_unit.brand:
            brand_name = job.ac_unit.brand.name

        defaults = {
            'business': job.business,
            'invoice_number': inv_num,
            'customer': job.customer,
            'technician': job.technician,
            'ac_brand': brand_name or "Multi-Brand",
            'service_description': f"[{job.get_appliance_type_display()}] {job.get_job_type_display()} - {job.complaint[:70]}",
            'service_charge': job.service_charge,
            'parts_charge': job.parts_charge,
            'discount': job.discount,
            'is_warranty': job.is_warranty,
            'dealer': job.warranty_dealer,
            'dealer_claim_status': job.dealer_claim_status,
            'dealer_claim_amount': job.dealer_claim_amount,
            'paid_at': job.paid_at,
        }

        if job.is_warranty:
            defaults['total_amount'] = Decimal('0.00')
            defaults['payment_status'] = 'WARRANTY'
            defaults['payment_method'] = 'DEALER_CLAIM'
            defaults['notes'] = f"WTY Claim: {job.warranty_dealer.name if job.warranty_dealer else 'Authorized Dealer'} [{brand_name}]"
        else:
            defaults['total_amount'] = job.total_amount
            defaults['payment_status'] = job.payment_status
            defaults['payment_method'] = job.payment_method or 'CASH'
            if job.payment_status == 'PAID':
                defaults['amount_paid'] = job.total_amount

        invoice, created = cls.objects.update_or_create(
            job=job,
            defaults=defaults
        )
        return invoice


class Payment(models.Model):
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='payments')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_method = models.CharField(max_length=20, default='CASH')
    reference = models.CharField(max_length=100, blank=True)
    received_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    notes = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Payment Rs. {self.amount} for {self.invoice.invoice_number} via {self.payment_method}"
