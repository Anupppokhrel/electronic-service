from django.db import models
from django.db.models import Sum
from core.models import Business

class Customer(models.Model):
    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name='customers')
    name = models.CharField(max_length=150)
    phone = models.CharField(max_length=30, db_index=True)
    alt_phone = models.CharField(max_length=30, blank=True)
    address = models.CharField(max_length=255, blank=True, default="")
    landmark = models.CharField(max_length=150, blank=True)
    email = models.EmailField(blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']
        unique_together = ('business', 'phone')

    def __str__(self):
        return f"{self.name} ({self.phone})"

    @property
    def total_jobs(self):
        return self.service_jobs.count()

    @property
    def last_service(self):
        last_job = self.service_jobs.order_by('-created_at').first()
        return last_job.created_at if last_job else None

    @property
    def total_spent(self):
        # Sum all service jobs total amounts
        spent = self.service_jobs.filter(payment_status='PAID').aggregate(total=Sum('total_amount'))['total']
        return spent or 0

    @property
    def total_due(self):
        # Outstanding unpaid credit balance (Deuu)
        due = self.service_jobs.filter(
            is_warranty=False,
            payment_status='PENDING',
            status__in=['COMPLETED', 'CLOSED', 'PAYMENT_PENDING']
        ).aggregate(total=Sum('total_amount'))['total']
        return due or 0
