from django.db import models
from django.contrib.auth.models import User

class Business(models.Model):
    name = models.CharField(max_length=150, default="Damak Multi-Brand AC & Appliance Service Center")
    tagline = models.CharField(max_length=200, default="Expert AC, Refrigerator, Washing Machine & Cooler Service")
    owner_name = models.CharField(max_length=100, default="Workshop Owner")
    phone = models.CharField(max_length=30, default="9842622354")
    alt_phone = models.CharField(max_length=30, blank=True, default="023-580123")
    email = models.EmailField(blank=True, default="service@damakappliances.com")
    address = models.CharField(max_length=255, default="Damak-05, Kirat Chowk, Jhapa, Nepal")
    pan_number = models.CharField(max_length=50, blank=True, default="304859201")
    currency_symbol = models.CharField(max_length=10, default="Rs.")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "Businesses"

    def __str__(self):
        return self.name

class PaymentQR(models.Model):
    QR_TYPES = [
        ('ESEWA', 'eSewa QR'),
        ('FONEPAY', 'Fonepay QR'),
        ('BANK', 'Bank QR'),
        ('OTHER', 'Other Payment QR'),
    ]

    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name='payment_qrs')
    qr_type = models.CharField(max_length=20, choices=QR_TYPES)
    title = models.CharField(max_length=100)
    account_name = models.CharField(max_length=120)
    account_number = models.CharField(max_length=100, blank=True)
    qr_image = models.ImageField(upload_to='payment_qrs/', blank=True, null=True)
    is_active = models.BooleanField(default=True)
    display_order = models.PositiveIntegerField(default=1)
    notes = models.CharField(max_length=255, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['display_order', 'id']

    def __str__(self):
        return f"{self.get_qr_type_display()} - {self.title}"

class ActivityLog(models.Model):
    ACTION_TYPES = [
        ('JOB_UPDATE', 'Job Status/Work Update'),
        ('STOCK_UPDATE', 'Inventory/Stock Change'),
        ('PAYMENT', 'Payment Record'),
        ('SYSTEM', 'System/Settings Change'),
        ('STAFF', 'Staff Activity'),
    ]

    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name='activity_logs')
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='activities')
    action = models.CharField(max_length=255)
    action_type = models.CharField(max_length=30, choices=ACTION_TYPES, default='JOB_UPDATE')
    job_reference = models.CharField(max_length=50, blank=True)
    details = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.action} ({self.created_at.strftime('%H:%M')})"
