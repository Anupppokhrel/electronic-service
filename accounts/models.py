from django.db import models
from django.contrib.auth.models import User
from core.models import Business

class StaffProfile(models.Model):
    ROLE_CHOICES = [
        ('ADMIN', 'Admin / Owner'),
        ('TECHNICIAN', 'Technician / Staff'),
    ]

    STATUS_CHOICES = [
        ('AVAILABLE', 'Available'),
        ('WORKING', 'Working'),
        ('ON_LEAVE', 'On Leave'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='staff_profile')
    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name='staff_members')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='TECHNICIAN')
    phone = models.CharField(max_length=20, blank=True)
    emergency_contact = models.CharField(max_length=20, blank=True)
    address = models.CharField(max_length=255, blank=True, default="")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='AVAILABLE')
    specialization = models.CharField(max_length=200, blank=True, default="Multi-Brand Inverter & Split AC")
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)
    joining_date = models.DateField(auto_now_add=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['user__first_name', 'user__username']

    def __str__(self):
        full_name = self.user.get_full_name()
        return full_name if full_name else self.user.username

    @property
    def is_admin(self):
        return self.role == 'ADMIN' or self.user.is_superuser

    @property
    def is_technician(self):
        return self.role == 'TECHNICIAN' and not self.user.is_superuser

    def get_active_job(self):
        # ServiceJob will be imported or queried dynamically to avoid circular import
        from services.models import ServiceJob
        return self.user.assigned_jobs.filter(status='IN_PROGRESS').first()

    def get_today_jobs(self):
        from django.utils import timezone
        today = timezone.localdate()
        return self.user.assigned_jobs.filter(created_at__date=today)

    def get_completed_jobs_count(self):
        return self.user.assigned_jobs.filter(status__in=['COMPLETED', 'CLOSED']).count()
