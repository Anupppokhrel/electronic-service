from django.test import TestCase, Client
from django.contrib.auth.models import User
from core.models import Business
from customers.models import Customer
from accounts.models import StaffProfile

class CustomerLookupTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.business = Business.objects.create(name="Chitwan AC Workshop")
        self.user = User.objects.create_user(username="testadmin", password="password")
        StaffProfile.objects.create(user=self.user, business=self.business, role='ADMIN')
        self.client.login(username="testadmin", password="password")

        self.customer = Customer.objects.create(
            business=self.business,
            name="Ram Kumar",
            phone="9841000001",
            address="Bharatpur-10, Chitwan"
        )

    def test_customer_lookup_api(self):
        response = self.client.get('/customers/lookup/?phone=9841000001')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['found'])
        self.assertEqual(data['name'], "Ram Kumar")
        self.assertEqual(data['address'], "Bharatpur-10, Chitwan")

    def test_customer_lookup_not_found(self):
        response = self.client.get('/customers/lookup/?phone=9800000000')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertFalse(data['found'])
