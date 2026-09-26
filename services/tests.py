from django.test import TestCase, Client
from django.contrib.auth.models import User
from decimal import Decimal
from core.models import Business
from accounts.models import StaffProfile
from customers.models import Customer
from inventory.models import Brand, InventoryItem
from services.models import ServiceJob, JobPart, WorkLog
from billing.models import Invoice

class ServiceJobWorkflowTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.business = Business.objects.create(name="Chitwan AC Workshop")
        self.user = User.objects.create_user(username="anup_test", password="password", first_name="Anup", last_name="Pokhrel")
        self.profile = StaffProfile.objects.create(user=self.user, business=self.business, role='TECHNICIAN')
        self.client.login(username="anup_test", password="password")

        self.customer = Customer.objects.create(
            business=self.business,
            name="Ram Kumar",
            phone="9841000001",
            address="Bharatpur-10, Chitwan"
        )

        self.brand = Brand.objects.create(business=self.business, name="LG")
        self.cap = InventoryItem.objects.create(
            business=self.business,
            part_name="LG Capacitor 45µF",
            brand=self.brand,
            quantity=Decimal('5.00'),
            minimum_stock=Decimal('3.00'),
            selling_price=Decimal('650.00')
        )

        self.job = ServiceJob.objects.create(
            business=self.business,
            job_number="JOB-2026-00482",
            customer=self.customer,
            ac_brand_name="LG",
            ac_type_name="Split AC",
            ac_capacity_name="1.5 Ton",
            service_type="AC Not Cooling",
            complaint="AC not cooling",
            technician=self.user,
            status="ASSIGNED",
            service_charge=Decimal('1500.00'),
            total_amount=Decimal('1500.00')
        )
        Invoice.sync_from_job(self.job)

    def test_job_start_work(self):
        response = self.client.post(f'/services/{self.job.id}/status/', {'action': 'START_WORK'})
        self.job.refresh_from_db()
        self.assertEqual(self.job.status, 'IN_PROGRESS')
        self.assertIsNotNone(self.job.start_time)
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.status, 'WORKING')

    def test_job_add_part_and_sync_invoice(self):
        # Add 1 LG Capacitor
        response = self.client.post(f'/services/{self.job.id}/parts/add/', {
            'inventory_item': self.cap.id,
            'quantity': '1',
            'unit_price': '650.00'
        })
        self.job.refresh_from_db()
        self.cap.refresh_from_db()

        self.assertEqual(self.cap.quantity, Decimal('4.00'))
        self.assertEqual(self.job.parts_charge, Decimal('650.00'))
        self.assertEqual(self.job.total_amount, Decimal('2150.00')) # 1500 + 650

        # Check internal invoice synced
        invoice = Invoice.objects.get(job=self.job)
        self.assertEqual(invoice.total_amount, Decimal('2150.00'))
        self.assertEqual(invoice.parts_charge, Decimal('650.00'))

    def test_job_payment_and_close(self):
        admin_user = User.objects.create_user(username="admin_test", password="password")
        StaffProfile.objects.create(user=admin_user, business=self.business, role='ADMIN')
        self.client.login(username="admin_test", password="password")

        response = self.client.post(f'/services/{self.job.id}/payment/', {
            'payment_method': 'ESEWA',
            'payment_reference': 'TXN994829',
            'mark_closed': 'on'
        })
        self.job.refresh_from_db()
        self.assertEqual(self.job.payment_status, 'PAID')
        self.assertEqual(self.job.payment_method, 'ESEWA')
        self.assertEqual(self.job.status, 'CLOSED')

        invoice = Invoice.objects.get(job=self.job)
        self.assertEqual(invoice.payment_status, 'PAID')
        self.assertEqual(invoice.payment_method, 'ESEWA')
