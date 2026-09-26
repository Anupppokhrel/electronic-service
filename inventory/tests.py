from django.test import TestCase
from decimal import Decimal
from django.contrib.auth.models import User
from core.models import Business
from inventory.models import Brand, Category, InventoryItem, StockTransaction
from customers.models import Customer
from services.models import ServiceJob, JobPart

class InventoryAutomationTestCase(TestCase):
    def setUp(self):
        self.business = Business.objects.create(name="Test Workshop")
        self.user = User.objects.create_user(username="tech_test", password="password")
        self.brand = Brand.objects.create(business=self.business, name="LG")
        self.item = InventoryItem.objects.create(
            business=self.business,
            part_name="LG Capacitor 45uF",
            part_code="CAP-45",
            brand=self.brand,
            quantity=Decimal('5.00'),
            minimum_stock=Decimal('3.00'),
            purchase_price=Decimal('400.00'),
            selling_price=Decimal('650.00')
        )
        self.customer = Customer.objects.create(
            business=self.business,
            name="Test Customer",
            phone="9841112233"
        )
        self.job = ServiceJob.objects.create(
            business=self.business,
            job_number="JOB-2026-99999",
            customer=self.customer,
            complaint="Not cooling",
            service_charge=Decimal('1500.00')
        )

    def test_stock_deduction_and_transaction(self):
        # Initial stock is 5
        self.assertEqual(self.item.quantity, Decimal('5.00'))

        # Add part used
        qty_used = Decimal('2.00')
        self.item.quantity -= qty_used
        self.item.save()

        StockTransaction.objects.create(
            item=self.item,
            transaction_type='SERVICE_USAGE',
            quantity_change=-qty_used,
            balance_after=self.item.quantity,
            unit_price=self.item.selling_price,
            job_reference=self.job.job_number,
            performed_by=self.user
        )

        JobPart.objects.create(
            job=self.job,
            inventory_item=self.item,
            quantity=qty_used,
            unit_price=self.item.selling_price
        )
        self.job.recalculate_totals()

        self.assertEqual(self.item.quantity, Decimal('3.00'))
        self.assertTrue(self.item.is_low_stock) # min is 3.00, so <= 3 is low stock!
        self.assertEqual(self.job.parts_charge, Decimal('1300.00')) # 2 * 650
        self.assertEqual(self.job.total_amount, Decimal('2800.00')) # 1500 + 1300

    def test_stock_return_on_removal(self):
        # Deduct
        self.item.quantity -= Decimal('1.00')
        self.item.save()
        part = JobPart.objects.create(
            job=self.job,
            inventory_item=self.item,
            quantity=Decimal('1.00'),
            unit_price=Decimal('650.00')
        )

        # Restore
        self.item.quantity += part.quantity
        self.item.save()
        part.delete()
        self.job.recalculate_totals()

        self.assertEqual(self.item.quantity, Decimal('5.00'))
        self.assertEqual(self.job.parts_charge, Decimal('0.00'))
        self.assertEqual(self.job.total_amount, Decimal('1500.00'))
