from django.test import TestCase, Client
from django.contrib.auth.models import User
from decimal import Decimal
from core.models import Business
from accounts.models import StaffProfile
from customers.models import Customer
from services.models import ServiceJob

class ReportsExportTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.business = Business.objects.create(name="Chitwan AC Workshop")
        self.user = User.objects.create_user(username="admin_rep", password="password")
        StaffProfile.objects.create(user=self.user, business=self.business, role='ADMIN')
        self.client.login(username="admin_rep", password="password")

        self.customer = Customer.objects.create(
            business=self.business,
            name="Sita Sharma",
            phone="9855000002",
            address="Narayangarh"
        )
        ServiceJob.objects.create(
            business=self.business,
            job_number="JOB-2026-00481",
            customer=self.customer,
            complaint="General service",
            service_charge=Decimal('1800.00'),
            total_amount=Decimal('1800.00'),
            status="COMPLETED",
            payment_status="PAID"
        )

    def test_reports_page_status(self):
        response = self.client.get('/reports/')
        self.assertEqual(response.status_code, 200)

    def test_export_jobs_csv(self):
        response = self.client.get('/reports/export/csv/?range=today')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/csv')
        self.assertIn('JOB-2026-00481', response.content.decode('utf-8'))

    def test_export_jobs_excel(self):
        response = self.client.get('/reports/export/excel/?range=today')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        self.assertTrue(len(response.content) > 0)
