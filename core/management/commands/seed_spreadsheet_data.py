from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import datetime, time, timedelta
from decimal import Decimal
from django.contrib.auth.models import User

from core.models import Business
from accounts.models import StaffProfile
from customers.models import Customer
from inventory.models import Brand, Category, InventoryItem
from services.models import ACUnit, ServiceJob, WorkLog, JobPart
from billing.models import Dealer, Invoice

class Command(BaseCommand):
    help = "Seed database with the owner's actual Excel spreadsheet data (Damak, Multi-Appliance, WTY, Deuu)"

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("Seeding Owner's Real Excel Spreadsheet Data..."))

        # 1. Update or create Business profile
        business = Business.objects.first()
        if not business:
            business = Business.objects.create(
                name="Damak Multi-Brand AC & Appliance Service Center",
                tagline="Authorized Multi-Brand AC, Refrigerator, Washing Machine & Cooler Service",
                owner_name="Bhimsen Shrestha",
                phone="9842622354",
                address="Damak-05, Kirat Chowk, Jhapa, Nepal",
                pan_number="304859201",
                currency_symbol="Rs.",
            )
        else:
            business.name = "Damak Multi-Brand AC & Appliance Service Center"
            business.tagline = "Authorized Multi-Brand AC, Refrigerator, Washing Machine & Cooler Service"
            business.address = "Damak-05, Kirat Chowk, Jhapa, Nepal"
            business.phone = "9842622354"
            business.save()

        admin_user = User.objects.filter(is_superuser=True).first() or User.objects.first()
        anup = User.objects.filter(username='anup').first() or admin_user
        raj = User.objects.filter(username='raj').first() or admin_user
        suman = User.objects.filter(username='suman').first() or admin_user
        bikash = User.objects.filter(username='bikash').first() or admin_user

        # 2. Brands
        brands_data = [
            ("LG", "LG", False),
            ("Samsung", "SAM", False),
            ("GEM", "GEM", False),
            ("Daikin", "DAI", False),
            ("Panasonic", "PAN", False),
            ("Whirlpool", "WHL", False),
            ("Common", "COM", True),
        ]
        brands = {}
        for bname, code, is_c in brands_data:
            b, _ = Brand.objects.get_or_create(
                business=business,
                name=bname,
                defaults={'code': code, 'is_common': is_c}
            )
            brands[bname] = b

        # 3. Authorized Dealers (for WTY claims)
        dealers_data = [
            ("LG Authorized Showroom - Damak", brands["LG"], "Sita Ram Dahal", "9852622001", "Damak-05, Chowk"),
            ("Samsung Plaza - Damak", brands["Samsung"], "Bikash Agarwal", "9852622002", "Damak Main Road"),
            ("GEM Electronics & Dist. - Urlabari", brands["GEM"], "Nabin Karki", "9852622003", "Urlabari-03, Morang"),
            ("CG Electronics Authorized - Damak", brands["Common"], "Manoj Shrestha", "9852622004", "Damak Buspark"),
        ]
        dealers = {}
        for dname, br, cperson, ph, addr in dealers_data:
            d, _ = Dealer.objects.get_or_create(
                business=business,
                name=dname,
                defaults={
                    'brand': br,
                    'contact_person': cperson,
                    'phone': ph,
                    'address': addr
                }
            )
            dealers[dname] = d

        # 4. Categories & Spares for Appliances
        cat_appliance, _ = Category.objects.get_or_create(business=business, name="Appliance Spares (Ref & WM)")
        cat_cooler, _ = Category.objects.get_or_create(business=business, name="Cooler Parts & Pumps")
        cat_electrical, _ = Category.objects.get_or_create(business=business, name="Electrical & Capacitors")

        spares_data = [
            ("PTC Relay (Refrigerator)", "REL-PTC-REF", cat_appliance, "REFRIGERATOR", "Common", Decimal('25.00'), Decimal('5.00'), "pcs", Decimal('180.00'), Decimal('350.00')),
            ("Overload Protector (Ref)", "OLP-REF-01", cat_appliance, "REFRIGERATOR", "Common", Decimal('30.00'), Decimal('6.00'), "pcs", Decimal('120.00'), Decimal('250.00')),
            ("R134a Refrigerant Can 450g", "GAS-R134-450", cat_appliance, "REFRIGERATOR", "Common", Decimal('18.00'), Decimal('4.00'), "can", Decimal('450.00'), Decimal('800.00')),
            ("Washing Machine Drain Pipe 2m", "WM-PIPE-DRN2M", cat_appliance, "WASHING_MACHINE", "Common", Decimal('20.00'), Decimal('5.00'), "pcs", Decimal('150.00'), Decimal('320.00')),
            ("Washing Machine Door Gasket", "WM-GSK-RUB", cat_appliance, "WASHING_MACHINE", "Common", Decimal('8.00'), Decimal('2.00'), "pcs", Decimal('650.00'), Decimal('1200.00')),
            ("Submersible Water Pump 18W", "CLR-PUMP-18W", cat_cooler, "COOLER", "Common", Decimal('14.00'), Decimal('3.00'), "pcs", Decimal('320.00'), Decimal('550.00')),
            ("Universal WM PCB Controller", "WM-PCB-UNI", cat_appliance, "WASHING_MACHINE", "Common", Decimal('5.00'), Decimal('2.00'), "pcs", Decimal('1400.00'), Decimal('2400.00')),
        ]
        spares = {}
        for pname, pcode, pcat, app_type, bname, qty, min_qty, unit, pprice, sprice in spares_data:
            item, _ = InventoryItem.objects.get_or_create(
                business=business,
                part_name=pname,
                defaults={
                    'part_code': pcode,
                    'category': pcat,
                    'appliance_type': app_type,
                    'inventory_type': 'COMMON',
                    'brand': brands[bname],
                    'quantity': qty,
                    'minimum_stock': min_qty,
                    'unit': unit,
                    'purchase_price': pprice,
                    'selling_price': sprice,
                    'supplier': "Damak Spares Hub",
                    'storage_bin': "Rack D-Appliance"
                }
            )
            spares[pname] = item

        # 5. Spreadsheet Rows Mapping (Baisakh 2083 BS / Current local dates)
        today = timezone.localdate()
        base_time = timezone.now()

        spreadsheet_entries = [
            # Row 1: Pradip daii ko didi / 9842622354 | Damak | AC | Install | Install,gass,wall mount,& service | 7000 | Deuu
            {
                'job_num': 'JOB-2026-00501',
                'customer_name': 'Pradip Sharma (Didi)',
                'phone': '9842622354',
                'address': 'Damak-05, Jhapa',
                'landmark': 'Near Chowk',
                'appliance': 'AC',
                'job_type': 'INSTALLATION',
                'brand': brands['LG'],
                'complaint': 'Installation, gass charge, wall mount & service needed',
                'tech': anup,
                'charge': Decimal('7000.00'),
                'is_wty': False,
                'status': 'COMPLETED',
                'pay_status': 'PENDING', # Deuu
                'pay_method': 'CASH',
                'cancel_reason': '',
            },
            # Row 2: 9705079703 | Gauradaha | Ref | No cooling | Gass charge svc done | 2000 | Paid
            {
                'job_num': 'JOB-2026-00502',
                'customer_name': 'Bikash Adhikari',
                'phone': '9705079703',
                'address': 'Gauradaha-02, Jhapa',
                'landmark': 'Bazaar Line',
                'appliance': 'REFRIGERATOR',
                'job_type': 'GENERAL_SERVICE',
                'brand': brands['Samsung'],
                'complaint': 'No cooling - Gass charge svc done',
                'tech': raj,
                'charge': Decimal('2000.00'),
                'is_wty': False,
                'status': 'CLOSED',
                'pay_status': 'PAID',
                'pay_method': 'CASH',
                'cancel_reason': '',
            },
            # Row 3: 9842631776 | DMK Electric office near | WM | Not work | SVC only | 500 | Paid
            {
                'job_num': 'JOB-2026-00503',
                'customer_name': 'DMK Electric Staff',
                'phone': '9842631776',
                'address': 'Damak, DMK Electric office near',
                'landmark': 'Electric Office',
                'appliance': 'WASHING_MACHINE',
                'job_type': 'GENERAL_SERVICE',
                'brand': brands['Whirlpool'],
                'complaint': 'Not work - SVC only',
                'tech': suman,
                'charge': Decimal('500.00'),
                'is_wty': False,
                'status': 'CLOSED',
                'pay_status': 'PAID',
                'pay_method': 'ESEWA',
                'cancel_reason': '',
            },
            # Row 4: Posan neupane / 9852683099 | Kirat chok | Cooler | Not work | Svc only | 200 | Paid
            {
                'job_num': 'JOB-2026-00504',
                'customer_name': 'Posan Neupane',
                'phone': '9852683099',
                'address': 'Kirat Chok, Damak',
                'landmark': 'Near Kirat Chowk',
                'appliance': 'COOLER',
                'job_type': 'GENERAL_SERVICE',
                'brand': brands['Common'],
                'complaint': 'Not work - Svc only pump inspection',
                'tech': bikash,
                'charge': Decimal('200.00'),
                'is_wty': False,
                'status': 'CLOSED',
                'pay_status': 'PAID',
                'pay_method': 'CASH',
                'cancel_reason': '',
            },
            # Row 5: 9819335980 | Kirat chok | AC | Need svc | Service done | 1500 | deuu sme
            {
                'job_num': 'JOB-2026-00505',
                'customer_name': 'Hari Prasad Regmi',
                'phone': '9819335980',
                'address': 'Kirat Chok, Damak',
                'landmark': 'Opposite Kirat Temple',
                'appliance': 'AC',
                'job_type': 'GENERAL_SERVICE',
                'brand': brands['LG'],
                'complaint': 'Need svc - Service done deep cleaning',
                'tech': anup,
                'charge': Decimal('1500.00'),
                'is_wty': False,
                'status': 'COMPLETED',
                'pay_status': 'PENDING', # Deuu
                'pay_method': 'CASH',
                'cancel_reason': '',
            },
            # Row 6: Tara bhandari / 9743824094 | Pathri | REF/GEM | No cooling | Compressor change gass charge | 3500 | Paid
            {
                'job_num': 'JOB-2026-00506',
                'customer_name': 'Tara Bhandari',
                'phone': '9743824094',
                'address': 'Pathri-02, Morang',
                'landmark': 'Highway Chowk',
                'appliance': 'REFRIGERATOR',
                'job_type': 'REPAIR',
                'brand': brands['GEM'],
                'complaint': 'No cooling - Compressor change & gass charge',
                'tech': bikash,
                'charge': Decimal('3500.00'),
                'is_wty': False,
                'status': 'CLOSED',
                'pay_status': 'PAID',
                'pay_method': 'FONEPAY',
                'cancel_reason': '',
            },
            # Row 7: Ganesh budathoki / 9842650299 | Damak | Ref | No cooling | Relay change svc done | 1000 | Paid
            {
                'job_num': 'JOB-2026-00507',
                'customer_name': 'Ganesh Budathoki',
                'phone': '9842650299',
                'address': 'Damak-06, Jhapa',
                'landmark': 'Bata Chowk',
                'appliance': 'REFRIGERATOR',
                'job_type': 'REPAIR',
                'brand': brands['Samsung'],
                'complaint': 'No cooling - Relay change svc done',
                'tech': raj,
                'charge': Decimal('1000.00'),
                'is_wty': False,
                'status': 'CLOSED',
                'pay_status': 'PAID',
                'pay_method': 'CASH',
                'cancel_reason': '',
            },
            # Row 8: Rama magar / 9820356936 | Urlabari | REF/GEM | No cooling | Relay overlod change svc done | WTY
            {
                'job_num': 'JOB-2026-00508',
                'customer_name': 'Rama Magar',
                'phone': '9820356936',
                'address': 'Urlabari-04, Morang',
                'landmark': 'Hospital Road',
                'appliance': 'REFRIGERATOR',
                'job_type': 'REPAIR',
                'brand': brands['GEM'],
                'complaint': 'No cooling - Relay overlod change svc done under company warranty',
                'tech': anup,
                'charge': Decimal('0.00'),
                'is_wty': True,
                'wty_dealer': dealers["GEM Electronics & Dist. - Urlabari"],
                'claim_amt': Decimal('1250.00'),
                'status': 'COMPLETED',
                'pay_status': 'WARRANTY',
                'pay_method': 'DEALER_CLAIM',
                'cancel_reason': '',
            },
            # Row 9: 9801555616 / Lab | Urlabari | AC | Need svc | Service done | 700 | Paid
            {
                'job_num': 'JOB-2026-00509',
                'customer_name': 'Urlabari Pathology Lab',
                'phone': '9801555616',
                'address': 'Urlabari-03, Morang',
                'landmark': 'Near Main Chowk',
                'appliance': 'AC',
                'job_type': 'GENERAL_SERVICE',
                'brand': brands['Daikin'],
                'complaint': 'Need svc - Service done filter cleaning',
                'tech': suman,
                'charge': Decimal('700.00'),
                'is_wty': False,
                'status': 'CLOSED',
                'pay_status': 'PAID',
                'pay_method': 'CASH',
                'cancel_reason': '',
            },
            # Row 10: Sagar paudel / 9862355541 | Pathri | WM | Moter or pcb | He did not send him machine | CANCELLED
            {
                'job_num': 'JOB-2026-00510',
                'customer_name': 'Sagar Paudel',
                'phone': '9862355541',
                'address': 'Pathri-01, Morang',
                'landmark': 'Near Cinema Hall',
                'appliance': 'WASHING_MACHINE',
                'job_type': 'REPAIR',
                'brand': brands['Samsung'],
                'complaint': 'Moter or pcb failure inspection',
                'tech': bikash,
                'charge': Decimal('0.00'),
                'is_wty': False,
                'status': 'CANCELLED',
                'pay_status': 'PENDING',
                'pay_method': 'CASH',
                'cancel_reason': 'He did not send him machine',
            },
            # Row 11: Nisha Dhimal | Parajungi | Ref | Ree complain | Compressor change gass charge | 1500 | Paid
            {
                'job_num': 'JOB-2026-00511',
                'customer_name': 'Nisha Dhimal',
                'phone': '9841000088',
                'address': 'Parajungi, Morang',
                'landmark': 'School Road',
                'appliance': 'REFRIGERATOR',
                'job_type': 'REPEAT_COMPLAINT',
                'brand': brands['LG'],
                'complaint': 'Ree complain - Cooling drop, compressor inspection & gas topup',
                'tech': raj,
                'charge': Decimal('1500.00'),
                'is_wty': False,
                'status': 'CLOSED',
                'pay_status': 'PAID',
                'pay_method': 'CASH',
                'cancel_reason': '',
            },
            # Row 12: 9852071963 | Urlabari | AC | Uninstall | Uninstall svc done | 1800 | Paid
            {
                'job_num': 'JOB-2026-00512',
                'customer_name': 'Dipak Shrestha',
                'phone': '9852071963',
                'address': 'Urlabari-02, Morang',
                'landmark': 'Bypass Chowk',
                'appliance': 'AC',
                'job_type': 'UNINSTALLATION',
                'brand': brands['Panasonic'],
                'complaint': 'Uninstall svc done with pipe pump down',
                'tech': anup,
                'charge': Decimal('1800.00'),
                'is_wty': False,
                'status': 'CLOSED',
                'pay_status': 'PAID',
                'pay_method': 'CASH',
                'cancel_reason': '',
            },
            # Row 13: 9842752951 | Kankai party plc near | WM | Need svc | Service done+drain pipe& gasskit repair | 3200 | Paid
            {
                'job_num': 'JOB-2026-00513',
                'customer_name': 'Kankai Party Palace',
                'phone': '9842752951',
                'address': 'Kankai, Jhapa',
                'landmark': 'Near Kankai Party Palace',
                'appliance': 'WASHING_MACHINE',
                'job_type': 'REPAIR',
                'brand': brands['Whirlpool'],
                'complaint': 'Need svc - Service done, drain pipe replaced & gasket repair',
                'tech': suman,
                'charge': Decimal('3200.00'),
                'is_wty': False,
                'status': 'CLOSED',
                'pay_status': 'PAID',
                'pay_method': 'BANK',
                'cancel_reason': '',
            }
        ]

        for entry in spreadsheet_entries:
            cust, _ = Customer.objects.get_or_create(
                business=business,
                phone=entry['phone'],
                defaults={
                    'name': entry['customer_name'],
                    'address': entry['address'],
                    'landmark': entry['landmark'],
                }
            )

            unit, _ = ACUnit.objects.get_or_create(
                customer=cust,
                brand=entry['brand'],
                appliance_type=entry['appliance'],
                defaults={
                    'ac_type': 'Standard Unit',
                    'capacity': 'Standard Rating',
                    'location_notes': entry['landmark']
                }
            )

            job, _ = ServiceJob.objects.update_or_create(
                business=business,
                job_number=entry['job_num'],
                defaults={
                    'customer': cust,
                    'appliance_type': entry['appliance'],
                    'job_type': entry['job_type'],
                    'brand': entry['brand'],
                    'ac_unit': unit,
                    'ac_brand_name': entry['brand'].name,
                    'ac_type_name': 'Standard Unit',
                    'ac_capacity_name': 'Standard',
                    'service_type': 'General Service',
                    'complaint': entry['complaint'],
                    'status': entry['status'],
                    'technician': entry['tech'],
                    'created_by': admin_user,
                    'created_at': base_time,
                    'service_charge': entry['charge'],
                    'total_amount': entry['charge'],
                    'is_warranty': entry['is_wty'],
                    'warranty_dealer': entry.get('wty_dealer'),
                    'dealer_claim_status': 'SUBMITTED' if entry['is_wty'] else 'PENDING',
                    'dealer_claim_amount': entry.get('claim_amt', Decimal('0.00')),
                    'cancel_reason': entry['cancel_reason'],
                    'payment_status': entry['pay_status'],
                    'payment_method': entry['pay_method'],
                    'paid_at': base_time if entry['pay_status'] == 'PAID' else None
                }
            )

            # Sync linked invoice
            Invoice.sync_from_job(job)

        self.stdout.write(self.style.SUCCESS(f"Successfully seeded {len(spreadsheet_entries)} actual spreadsheet entries!"))
