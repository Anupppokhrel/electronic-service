import os
import random
from decimal import Decimal
from datetime import datetime, time, timedelta
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from PIL import Image, ImageDraw, ImageFont

from core.models import Business, PaymentQR, ActivityLog
from accounts.models import StaffProfile
from customers.models import Customer
from inventory.models import Brand, Category, InventoryItem, StockTransaction
from services.models import ACUnit, ServiceJob, WorkLog, JobPart
from billing.models import Invoice, Payment

def generate_mock_qr_image(filepath, text_label, brand_color=(30, 58, 138)):
    """Generates a realistic-looking mock payment QR image with brand banner."""
    width, height = 400, 480
    image = Image.new('RGB', (width, height), (255, 255, 255))
    draw = ImageDraw.Draw(image)

    # Top brand bar
    draw.rectangle([0, 0, width, 70], fill=brand_color)
    draw.text((width // 2, 35), text_label, fill=(255, 255, 255), anchor="mm")

    # Draw QR code boundary
    qr_left, qr_top = 40, 90
    qr_size = 320
    draw.rectangle([qr_left - 10, qr_top - 10, qr_left + qr_size + 10, qr_top + qr_size + 10], outline=(220, 220, 220), width=2)

    # Draw QR finder patterns (the three large squares in corners)
    def draw_finder(x, y):
        draw.rectangle([x, y, x + 64, y + 64], fill=(0, 0, 0))
        draw.rectangle([x + 8, y + 8, x + 56, y + 56], fill=(255, 255, 255))
        draw.rectangle([x + 16, y + 16, x + 48, y + 48], fill=(0, 0, 0))

    draw_finder(qr_left, qr_top)
    draw_finder(qr_left + qr_size - 64, qr_top)
    draw_finder(qr_left, qr_top + qr_size - 64)

    # Draw pseudo-random QR modules for realistic look
    grid_size = 25
    module_size = qr_size // grid_size
    random.seed(sum(ord(c) for c in text_label))
    for r in range(grid_size):
        for c in range(grid_size):
            # Skip finders
            if (r < 7 and c < 7) or (r < 7 and c > grid_size - 8) or (r > grid_size - 8 and c < 7):
                continue
            if random.random() > 0.5:
                mx = qr_left + c * module_size
                my = qr_top + r * module_size
                draw.rectangle([mx, my, mx + module_size - 1, my + module_size - 1], fill=(20, 25, 35))

    # Center logo box
    cx, cy = qr_left + qr_size // 2, qr_top + qr_size // 2
    draw.rectangle([cx - 24, cy - 24, cx + 24, cy + 24], fill=(255, 255, 255), outline=brand_color, width=3)
    draw.text((cx, cy), "PAY", fill=brand_color, anchor="mm")

    # Bottom scan prompt
    draw.text((width // 2, height - 35), "Scan & Pay via Mobile App", fill=(100, 116, 139), anchor="mm")

    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    image.save(filepath, "PNG")

class Command(BaseCommand):
    help = "Seed database with realistic multi-brand AC workshop dummy data"

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("Seeding Multi-Brand AC Workshop Data..."))

        # 1. Business
        business, _ = Business.objects.get_or_create(
            id=1,
            defaults={
                'name': "Chitwan Multi-Brand AC Service & Repair Workshop",
                'tagline': "Authorized Multi-Brand AC Servicing, Repair & Spare Parts",
                'owner_name': "Bhimsen Shrestha",
                'phone': "9855012345",
                'alt_phone': "056-520123",
                'email': "service@chitwanac.com",
                'address': "Bharatpur-10, Bypass Road, Chitwan, Nepal",
                'pan_number': "304859201",
                'currency_symbol': "Rs.",
            }
        )

        # 2. Staff & Users
        staff_data = [
            ("admin", "admin123", "Bhimsen", "Shrestha", "ADMIN", "9855012345", "AVAILABLE", "Proprietor & Lead Workshop Manager"),
            ("anup", "tech123", "Anup", "Pokhrel", "TECHNICIAN", "9841123456", "WORKING", "Senior Split & Inverter Specialist"),
            ("raj", "tech123", "Raj", "Thapa", "TECHNICIAN", "9845234567", "WORKING", "VRF / Ductable & Gas Diagnostics"),
            ("suman", "tech123", "Suman", "KC", "TECHNICIAN", "9860345678", "AVAILABLE", "PCB Electronics & Electrical Expert"),
            ("bikash", "tech123", "Bikash", "Gurung", "TECHNICIAN", "9812456789", "WORKING", "Compressor & Mechanical Repairs"),
        ]

        staff_users = {}
        for username, pwd, fname, lname, role, phone, status, spec in staff_data:
            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    'first_name': fname,
                    'last_name': lname,
                    'is_staff': (role == 'ADMIN'),
                    'is_superuser': (role == 'ADMIN'),
                    'email': f"{username}@chitwanac.com"
                }
            )
            if created or not user.check_password(pwd):
                user.set_password(pwd)
                user.first_name = fname
                user.last_name = lname
                user.is_staff = (role == 'ADMIN')
                user.is_superuser = (role == 'ADMIN')
                user.save()

            profile, _ = StaffProfile.objects.get_or_create(
                user=user,
                defaults={
                    'business': business,
                    'role': role,
                    'phone': phone,
                    'status': status,
                    'address': "Bharatpur, Chitwan",
                    'specialization': spec,
                }
            )
            profile.role = role
            profile.phone = phone
            profile.status = status
            profile.specialization = spec
            profile.save()
            staff_users[username] = user

        # 3. Brands
        brands_data = [
            ("LG", "LG", False, "LG Electronics Life's Good Inverter AC Units & Dual Inverter Spares"),
            ("Samsung", "SAM", False, "Samsung WindFree & Digital Inverter Air Conditioning"),
            ("Daikin", "DAI", False, "Daikin Japanese Precision Climate Systems & Inverter Spares"),
            ("Panasonic", "PAN", False, "Panasonic nanoe-X & EcoNavi Air Conditioners"),
            ("Gree", "GREE", False, "Gree Intelligent Air Conditioning & Commercial Inverters"),
            ("Voltas", "VOL", False, "Voltas High Ambient Cooling Systems & Spares"),
            ("Common", "COM", True, "Universal & Common Refrigeration Fittings, Piping, Gases and Capacitors"),
        ]

        brands = {}
        for name, code, is_com, desc in brands_data:
            b, _ = Brand.objects.get_or_create(
                business=business,
                name=name,
                defaults={'code': code, 'is_common': is_com, 'description': desc}
            )
            brands[name] = b

        # 4. Categories
        cat_names = [
            "Electrical & Capacitors",
            "PCB & Micro-Electronics",
            "Refrigerant Gases",
            "Copper Pipes & Fittings",
            "Motors, Blowers & Blades",
            "Consumables & Hardware",
            "Remotes & Sensors"
        ]
        categories = {}
        for cname in cat_names:
            c, _ = Category.objects.get_or_create(business=business, name=cname)
            categories[cname] = c

        # 5. Inventory Items (with LOW STOCK items matching requirement)
        inventory_data = [
            # Low stock items specified in prompt:
            ("Samsung PCB Board", "PCB-SAM-INV01", "PCB & Micro-Electronics", "BRAND_SPECIFIC", "Samsung", Decimal('2.00'), Decimal('3.00'), "pcs", Decimal('3200.00'), Decimal('4800.00'), "Samsung Nepal Authorized"),
            ("LG Capacitor 45µF", "CAP-LG-45UF", "Electrical & Capacitors", "BRAND_SPECIFIC", "LG", Decimal('4.00'), Decimal('5.00'), "pcs", Decimal('380.00'), Decimal('650.00'), "LG Spares Birgunj"),
            ("Copper Pipe 1/4\"", "PIPE-COP-025", "Copper Pipes & Fittings", "COMMON", "Common", Decimal('8.00'), Decimal('10.00'), "meter", Decimal('160.00'), Decimal('250.00'), "Bharatpur Metal Store"),
            
            # Healthy stock items
            ("Common Copper Pipe 3/8\"", "PIPE-COP-038", "Copper Pipes & Fittings", "COMMON", "Common", Decimal('45.00'), Decimal('15.00'), "meter", Decimal('240.00'), Decimal('380.00'), "Bharatpur Metal Store"),
            ("Common Copper Pipe 1/2\"", "PIPE-COP-050", "Copper Pipes & Fittings", "COMMON", "Common", Decimal('32.00'), Decimal('10.00'), "meter", Decimal('320.00'), Decimal('490.00'), "Bharatpur Metal Store"),
            ("R32 Refrigerant Gas (13.6kg)", "GAS-R32-CYL", "Refrigerant Gases", "COMMON", "Common", Decimal('6.00'), Decimal('2.00'), "can", Decimal('8500.00'), Decimal('12500.00'), "Nepal Gas Suppliers"),
            ("R410A Refrigerant Gas (11.3kg)", "GAS-R410A", "Refrigerant Gases", "COMMON", "Common", Decimal('5.00'), Decimal('2.00'), "can", Decimal('7800.00'), Decimal('11200.00'), "Nepal Gas Suppliers"),
            ("Daikin Indoor Fan Motor", "MOT-DAI-IFM", "Motors, Blowers & Blades", "BRAND_SPECIFIC", "Daikin", Decimal('3.00'), Decimal('2.00'), "pcs", Decimal('2400.00'), Decimal('3600.00'), "Daikin Direct Importers"),
            ("Panasonic Universal Remote", "REM-PAN-UNI", "Remotes & Sensors", "BRAND_SPECIFIC", "Panasonic", Decimal('12.00'), Decimal('4.00'), "pcs", Decimal('450.00'), Decimal('850.00'), "Chitwan Electronics"),
            ("LG Dual Inverter Outdoor Fan Blade", "BLD-LG-OUT", "Motors, Blowers & Blades", "BRAND_SPECIFIC", "LG", Decimal('5.00'), Decimal('2.00'), "pcs", Decimal('900.00'), Decimal('1500.00'), "LG Spares Birgunj"),
            ("Gree Inverter Ambient Sensor", "SEN-GREE-AMB", "PCB & Micro-Electronics", "BRAND_SPECIFIC", "Gree", Decimal('7.00'), Decimal('3.00'), "pcs", Decimal('250.00'), Decimal('550.00'), "Gree Service Center"),
            ("Common Insulation Tape & Sleeve (Black)", "INS-SLV-01", "Consumables & Hardware", "COMMON", "Common", Decimal('40.00'), Decimal('10.00'), "roll", Decimal('80.00'), Decimal('150.00'), "Narayangarh Hardware"),
            ("Brass Flare Nut 1/4\" & 3/8\" Set", "NUT-FLR-SET", "Copper Pipes & Fittings", "COMMON", "Common", Decimal('60.00'), Decimal('20.00'), "set", Decimal('90.00'), Decimal('180.00'), "Bharatpur Metal Store"),
        ]

        items = {}
        for name, code, cname, itype, bname, qty, min_qty, unit, pprice, sprice, supp in inventory_data:
            cat = categories[cname]
            br = brands[bname]
            item, created = InventoryItem.objects.get_or_create(
                business=business,
                part_name=name,
                defaults={
                    'part_code': code,
                    'category': cat,
                    'inventory_type': itype,
                    'brand': br,
                    'quantity': qty,
                    'minimum_stock': min_qty,
                    'unit': unit,
                    'purchase_price': pprice,
                    'selling_price': sprice,
                    'supplier': supp,
                    'storage_bin': "Rack B-03",
                    'notes': f"Genuine standard replacement component ({bname})"
                }
            )
            item.quantity = qty
            item.minimum_stock = min_qty
            item.selling_price = sprice
            item.save()
            items[name] = item

        # 6. Customers
        customers_data = [
            ("Ram Kumar", "9841000001", "Bharatpur-10, Chitwan", "Near Chaubiskothi"),
            ("Sita Sharma", "9855000002", "Narayangarh, Ward-1", "Opposite Lions Club"),
            ("Hari KC", "9845000003", "Tandi, Ratnanagar, Chitwan", "Near Bakulahar Hospital"),
            ("Mina Adhikari", "9860000004", "Gaindakot-2, Nawalpur", "Pulchowk Road"),
            ("Rameshwor Poudel", "9855000005", "Bharatpur-12, Chitwan", "Milanchowk"),
            ("Sunita Thapa", "9845000006", "Bharatpur-7, Krishnapur", "Shivalaya Marga"),
            ("Govinda Acharya", "9812000007", "Narayangarh, Main Bazaar", "Shahid Chowk"),
            ("Kamala Subedi", "9841000008", "Bharatpur-4, Lanku", "Near Eye Hospital"),
            ("Dr. Binod Shrestha", "9855000009", "Bharatpur-10, Chitwan", "Medical College Road"),
            ("Pooja Gurung", "9860000010", "Devghat-5, Tanahun", "River View"),
        ]

        customers = {}
        for cname, phone, addr, lmark in customers_data:
            c, _ = Customer.objects.get_or_create(
                business=business,
                phone=phone,
                defaults={'name': cname, 'address': addr, 'landmark': lmark}
            )
            c.name = cname
            c.address = addr
            c.save()
            customers[phone] = c

        # 7. AC Units for customers
        ac_units = {}
        ac_ram, _ = ACUnit.objects.get_or_create(
            customer=customers["9841000001"],
            brand=brands["LG"],
            defaults={
                'ac_type': 'Split AC',
                'capacity': '1.5 Ton',
                'model_number': 'LG-DUAL-COOL-18K',
                'serial_number': 'LG202598371',
                'location_notes': 'Living Room Hall'
            }
        )
        ac_units["Ram Kumar"] = ac_ram

        ac_sita, _ = ACUnit.objects.get_or_create(
            customer=customers["9855000002"],
            brand=brands["Samsung"],
            defaults={
                'ac_type': 'Split AC',
                'capacity': '1.5 Ton',
                'model_number': 'SAM-WINDFREE-18K',
                'serial_number': 'SAM893412',
                'location_notes': 'Master Bedroom'
            }
        )
        ac_units["Sita Sharma"] = ac_sita

        ac_hari, _ = ACUnit.objects.get_or_create(
            customer=customers["9845000003"],
            brand=brands["Daikin"],
            defaults={
                'ac_type': 'Split AC',
                'capacity': '2.0 Ton',
                'model_number': 'DAI-FTKF60',
                'serial_number': 'DAI774128',
                'location_notes': 'Clinic Front Room'
            }
        )
        ac_units["Hari KC"] = ac_hari

        ac_mina, _ = ACUnit.objects.get_or_create(
            customer=customers["9860000004"],
            brand=brands["Panasonic"],
            defaults={
                'ac_type': 'Split AC',
                'capacity': '1.0 Ton',
                'model_number': 'PAN-ECONAVI-12K',
                'serial_number': 'PAN339102',
                'location_notes': 'Kids Bedroom'
            }
        )
        ac_units["Mina Adhikari"] = ac_mina

        now = timezone.now()
        today = timezone.localdate()

        # 8. Create Ram Kumar's historical job: JOB-2026-00391 (June 11, 2026)
        date_june = timezone.make_aware(datetime(2026, 6, 11, 11, 30))
        job_391, _ = ServiceJob.objects.get_or_create(
            business=business,
            job_number="JOB-2026-00391",
            defaults={
                'customer': customers["9841000001"],
                'ac_unit': ac_ram,
                'ac_brand_name': "LG",
                'ac_type_name': "Split AC",
                'ac_capacity_name': "1.5 Ton",
                'service_type': "General Service",
                'complaint': "Periodic summer deep cleaning & routine cooling inspection",
                'status': "CLOSED",
                'technician': staff_users["anup"],
                'created_by': staff_users["admin"],
                'created_at': date_june,
                'start_time': date_june,
                'completion_time': date_june + timedelta(hours=1, minutes=20),
                'closed_at': date_june + timedelta(hours=1, minutes=30),
                'service_charge': Decimal('1800.00'),
                'parts_charge': Decimal('0.00'),
                'discount': Decimal('0.00'),
                'total_amount': Decimal('1800.00'),
                'payment_status': 'PAID',
                'payment_method': 'ESEWA',
                'paid_at': date_june + timedelta(hours=1, minutes=25),
            }
        )
        Invoice.sync_from_job(job_391)

        # 9. Today's Core Highlighted Jobs:
        # JOB-2026-00482 (Ram Kumar, LG, Anup Pokhrel, In Progress, 10:42 AM)
        t_10_42 = timezone.make_aware(datetime.combine(today, time(10, 42)))
        job_482, _ = ServiceJob.objects.get_or_create(
            business=business,
            job_number="JOB-2026-00482",
            defaults={
                'customer': customers["9841000001"],
                'ac_unit': ac_ram,
                'ac_brand_name': "LG",
                'ac_type_name': "Split AC",
                'ac_capacity_name': "1.5 Ton",
                'service_type': "AC Not Cooling",
                'complaint': "AC not cooling, indoor fan running but compressor humming without cooling",
                'status': "IN_PROGRESS",
                'technician': staff_users["anup"],
                'created_by': staff_users["admin"],
                'created_at': t_10_42 - timedelta(minutes=15),
                'start_time': t_10_42,
                'service_charge': Decimal('1500.00'),
                'parts_charge': Decimal('1150.00'),
                'discount': Decimal('0.00'),
                'total_amount': Decimal('2650.00'),
                'payment_status': 'PENDING',
                'payment_method': 'CASH',
            }
        )
        job_482.status = 'IN_PROGRESS'
        job_482.start_time = t_10_42
        job_482.service_charge = Decimal('1500.00')
        job_482.save()

        # Work performed logs for JOB-00482
        WorkLog.objects.filter(job=job_482).delete()
        WorkLog.objects.create(job=job_482, technician=staff_users["anup"], description="Gas pressure checked (R32 standing: 140 psi, suction: 65 psi)", created_at=t_10_42 + timedelta(minutes=5))
        WorkLog.objects.create(job=job_482, technician=staff_users["anup"], description="Indoor unit cleaned and condenser coil inspected", created_at=t_10_42 + timedelta(minutes=12))
        WorkLog.objects.create(job=job_482, technician=staff_users["anup"], description="Capacitor replaced (45µF dual terminal)", created_at=t_10_42 + timedelta(minutes=20))

        # Parts used for JOB-00482
        JobPart.objects.filter(job=job_482).delete()
        lg_cap = items["LG Capacitor 45µF"]
        p1 = JobPart.objects.create(
            job=job_482,
            inventory_item=lg_cap,
            quantity=Decimal('1.00'),
            unit_price=Decimal('650.00'),
            subtotal=Decimal('650.00'),
            added_by=staff_users["anup"],
            added_at=t_10_42 + timedelta(minutes=9)
        )
        cop_pipe = items["Copper Pipe 1/4\""]
        p2 = JobPart.objects.create(
            job=job_482,
            inventory_item=cop_pipe,
            quantity=Decimal('2.00'),
            unit_price=Decimal('250.00'),
            subtotal=Decimal('500.00'),
            added_by=staff_users["anup"],
            added_at=t_10_42 + timedelta(minutes=14)
        )
        # Note: 650 + 500 = 1,150 parts charge.
        job_482.recalculate_totals()

        # JOB-2026-00481 (Sita Sharma, Samsung, Raj Thapa, General Service, Completed 09:35 AM -> 10:18 AM)
        t_09_35 = timezone.make_aware(datetime.combine(today, time(9, 35)))
        t_10_18 = timezone.make_aware(datetime.combine(today, time(10, 18)))
        job_481, _ = ServiceJob.objects.get_or_create(
            business=business,
            job_number="JOB-2026-00481",
            defaults={
                'customer': customers["9855000002"],
                'ac_unit': ac_sita,
                'ac_brand_name': "Samsung",
                'ac_type_name': "Split AC",
                'ac_capacity_name': "1.5 Ton",
                'service_type': "General Service",
                'complaint': "Routine thorough pressure jet cleaning and anti-bacterial coil wash",
                'status': "COMPLETED",
                'technician': staff_users["raj"],
                'created_by': staff_users["admin"],
                'created_at': t_09_35 - timedelta(minutes=20),
                'start_time': t_09_35,
                'completion_time': t_10_18,
                'service_charge': Decimal('1800.00'),
                'parts_charge': Decimal('0.00'),
                'discount': Decimal('0.00'),
                'total_amount': Decimal('1800.00'),
                'payment_status': 'PAID',
                'payment_method': 'FONEPAY',
                'paid_at': t_10_18,
            }
        )
        WorkLog.objects.get_or_create(job=job_481, description="Pressure jet washed outdoor & indoor evaporator coils", defaults={'technician': staff_users["raj"]})
        WorkLog.objects.get_or_create(job=job_481, description="Blower wheel sanitized and drain line flushed", defaults={'technician': staff_users["raj"]})
        Invoice.sync_from_job(job_481)

        # JOB-2026-00480 (Hari KC, Daikin, Suman KC, PCB Replacement, Waiting for Parts, 09:10 AM)
        t_09_10 = timezone.make_aware(datetime.combine(today, time(9, 10)))
        job_480, _ = ServiceJob.objects.get_or_create(
            business=business,
            job_number="JOB-2026-00480",
            defaults={
                'customer': customers["9845000003"],
                'ac_unit': ac_hari,
                'ac_brand_name': "Daikin",
                'ac_type_name': "Split AC",
                'ac_capacity_name': "2.0 Ton",
                'service_type': "PCB Replacement",
                'complaint': "Inverter error code U4 - outdoor communication error; PCB burnt due to lightning surge",
                'status': "WAITING_FOR_PARTS",
                'technician': staff_users["suman"],
                'created_by': staff_users["admin"],
                'created_at': t_09_10 - timedelta(minutes=15),
                'start_time': t_09_10,
                'service_charge': Decimal('2200.00'),
                'parts_charge': Decimal('0.00'),
                'discount': Decimal('0.00'),
                'total_amount': Decimal('2200.00'),
                'payment_status': 'PENDING',
                'payment_method': 'BANK',
            }
        )
        WorkLog.objects.get_or_create(job=job_480, description="Outdoor inverter PCB circuit diagnosed: surge varistor & IPM blown", defaults={'technician': staff_users["suman"]})
        WorkLog.objects.get_or_create(job=job_480, description="Part requisitioned: Waiting for replacement Daikin Inverter PCB Board", defaults={'technician': staff_users["suman"]})
        Invoice.sync_from_job(job_480)

        # JOB-2026-00479 (Mina Adhikari, Panasonic, Bikash Gurung, Gas Charging, Completed 08:45 AM -> 10:00 AM)
        t_08_45 = timezone.make_aware(datetime.combine(today, time(8, 45)))
        t_10_00 = timezone.make_aware(datetime.combine(today, time(10, 0)))
        job_479, _ = ServiceJob.objects.get_or_create(
            business=business,
            job_number="JOB-2026-00479",
            defaults={
                'customer': customers["9860000004"],
                'ac_unit': ac_mina,
                'ac_brand_name': "Panasonic",
                'ac_type_name': "Split AC",
                'ac_capacity_name': "1.0 Ton",
                'service_type': "Gas Charging",
                'complaint': "Low cooling, ice forming on copper pipe; flare leak fixed & nitrogen pressure tested",
                'status': "COMPLETED",
                'technician': staff_users["bikash"],
                'created_by': staff_users["admin"],
                'created_at': t_08_45 - timedelta(minutes=25),
                'start_time': t_08_45,
                'completion_time': t_10_00,
                'service_charge': Decimal('1500.00'),
                'parts_charge': Decimal('1200.00'),
                'discount': Decimal('100.00'),
                'total_amount': Decimal('2600.00'),
                'payment_status': 'PAID',
                'payment_method': 'ESEWA',
                'paid_at': t_10_00,
            }
        )
        WorkLog.objects.get_or_create(job=job_479, description="Flare joint nut re-tightened & nitrogen leak test passed", defaults={'technician': staff_users["bikash"]})
        WorkLog.objects.get_or_create(job=job_479, description="Deep vacuum pulled to 500 microns and 750g R32 gas charged", defaults={'technician': staff_users["bikash"]})
        Invoice.sync_from_job(job_479)

        # Additional jobs for TODAY to reach exactly:
        # Today's Jobs: 12
        # New: 2
        # Assigned: 1
        # In Progress: 4 (job_482 + 3 more)
        # Waiting for Parts: 1 (job_480)
        # Completed: 5 (job_481, job_479 + 3 more completed/closed today)
        # Today's Revenue: Rs. 48,500
        
        # Current completed total = 1800 (job 481) + 2600 (job 479) = 4,400.
        # We need 3 more completed jobs whose sum + 4,400 = 48,500 (diff: 44,100).
        # Job A: Rs. 16,500 (Commercial VRF servicing & gas), Job B: Rs. 18,800, Job C: Rs. 8,800 -> 16500+18800+8800 = 44,100! Total = 48,500!
        
        # Completed Job A
        j_a, _ = ServiceJob.objects.get_or_create(
            business=business,
            job_number="JOB-2026-00478",
            defaults={
                'customer': customers["9855000009"], # Dr. Binod Shrestha
                'ac_brand_name': "Daikin",
                'ac_type_name': "Cassette AC",
                'ac_capacity_name': "3.0 Ton",
                'service_type': "General Service",
                'complaint': "Hospital clinic cassette AC complete chemical wash and blower motor maintenance",
                'status': "COMPLETED",
                'technician': staff_users["raj"],
                'created_by': staff_users["admin"],
                'created_at': t_08_45 - timedelta(hours=2),
                'start_time': t_08_45 - timedelta(hours=1, minutes=45),
                'completion_time': t_08_45 - timedelta(minutes=10),
                'service_charge': Decimal('8500.00'),
                'parts_charge': Decimal('8000.00'),
                'discount': Decimal('0.00'),
                'total_amount': Decimal('16500.00'),
                'payment_status': 'PAID',
                'payment_method': 'BANK',
                'paid_at': t_08_45 - timedelta(minutes=10),
            }
        )
        Invoice.sync_from_job(j_a)

        # Completed Job B
        j_b, _ = ServiceJob.objects.get_or_create(
            business=business,
            job_number="JOB-2026-00477",
            defaults={
                'customer': customers["9812000007"], # Govinda Acharya
                'ac_brand_name': "Gree",
                'ac_type_name': "Tower AC",
                'ac_capacity_name': "4.0+ Ton",
                'service_type': "Compressor Issue",
                'complaint': "Commercial hall tower AC compressor magnetic contactor & capacitor replacement",
                'status': "COMPLETED",
                'technician': staff_users["bikash"],
                'created_by': staff_users["admin"],
                'created_at': t_08_45 - timedelta(hours=3),
                'start_time': t_08_45 - timedelta(hours=2, minutes=30),
                'completion_time': t_08_45 - timedelta(hours=1),
                'service_charge': Decimal('6800.00'),
                'parts_charge': Decimal('12000.00'),
                'discount': Decimal('0.00'),
                'total_amount': Decimal('18800.00'),
                'payment_status': 'PAID',
                'payment_method': 'CASH',
                'paid_at': t_08_45 - timedelta(hours=1),
            }
        )
        Invoice.sync_from_job(j_b)

        # Completed Job C
        j_c, _ = ServiceJob.objects.get_or_create(
            business=business,
            job_number="JOB-2026-00476",
            defaults={
                'customer': customers["9855000005"], # Rameshwor Poudel
                'ac_brand_name': "Voltas",
                'ac_type_name': "Split AC",
                'ac_capacity_name': "2.0 Ton",
                'service_type': "Gas Charging",
                'complaint': "High ambient heat protection tripping, gas top-up and condenser wash",
                'status': "COMPLETED",
                'technician': staff_users["anup"],
                'created_by': staff_users["admin"],
                'created_at': t_08_45 - timedelta(hours=3, minutes=30),
                'start_time': t_08_45 - timedelta(hours=3),
                'completion_time': t_08_45 - timedelta(hours=1, minutes=30),
                'service_charge': Decimal('3200.00'),
                'parts_charge': Decimal('5600.00'),
                'discount': Decimal('0.00'),
                'total_amount': Decimal('8800.00'),
                'payment_status': 'PAID',
                'payment_method': 'FONEPAY',
                'paid_at': t_08_45 - timedelta(hours=1, minutes=30),
            }
        )
        Invoice.sync_from_job(j_c)

        # 3 other IN_PROGRESS jobs (making total 4 in progress):
        j_ip1, _ = ServiceJob.objects.get_or_create(
            business=business,
            job_number="JOB-2026-00483",
            defaults={
                'customer': customers["9845000006"], # Sunita Thapa
                'ac_brand_name': "Samsung",
                'ac_type_name': "Split AC",
                'ac_capacity_name': "1.5 Ton",
                'service_type': "Water Leakage",
                'complaint': "Water overflowing from indoor tray inside bedroom onto wall",
                'status': "IN_PROGRESS",
                'technician': staff_users["raj"],
                'created_by': staff_users["admin"],
                'created_at': t_10_42 - timedelta(minutes=30),
                'start_time': t_10_42 - timedelta(minutes=10),
                'service_charge': Decimal('1200.00'),
                'parts_charge': Decimal('0.00'),
                'discount': Decimal('0.00'),
                'total_amount': Decimal('1200.00'),
                'payment_status': 'PENDING',
            }
        )
        j_ip2, _ = ServiceJob.objects.get_or_create(
            business=business,
            job_number="JOB-2026-00484",
            defaults={
                'customer': customers["9841000008"], # Kamala Subedi
                'ac_brand_name': "LG",
                'ac_type_name': "Split AC",
                'ac_capacity_name': "1.0 Ton",
                'service_type': "Electrical Issue",
                'complaint': "MCB tripping whenever AC is powered on; outdoor fan motor check",
                'status': "IN_PROGRESS",
                'technician': staff_users["bikash"],
                'created_by': staff_users["admin"],
                'created_at': t_10_42 - timedelta(minutes=20),
                'start_time': t_10_42 - timedelta(minutes=5),
                'service_charge': Decimal('1800.00'),
                'parts_charge': Decimal('0.00'),
                'discount': Decimal('0.00'),
                'total_amount': Decimal('1800.00'),
                'payment_status': 'PENDING',
            }
        )
        j_ip3, _ = ServiceJob.objects.get_or_create(
            business=business,
            job_number="JOB-2026-00485",
            defaults={
                'customer': customers["9860000010"], # Pooja Gurung
                'ac_brand_name': "Panasonic",
                'ac_type_name': "Split AC",
                'ac_capacity_name': "1.5 Ton",
                'service_type': "General Service",
                'complaint': "Air conditioner foul smell when blowing; foam cleaning and drain line sanitizing",
                'status': "IN_PROGRESS",
                'technician': staff_users["anup"],
                'created_by': staff_users["admin"],
                'created_at': t_10_42 - timedelta(minutes=10),
                'start_time': t_10_42,
                'service_charge': Decimal('1600.00'),
                'parts_charge': Decimal('0.00'),
                'discount': Decimal('0.00'),
                'total_amount': Decimal('1600.00'),
                'payment_status': 'PENDING',
            }
        )

        # 1 ASSIGNED job:
        j_asg, _ = ServiceJob.objects.get_or_create(
            business=business,
            job_number="JOB-2026-00486",
            defaults={
                'customer': customers["9812000007"],
                'ac_brand_name': "Voltas",
                'ac_type_name': "Split AC",
                'ac_capacity_name': "1.5 Ton",
                'service_type': "Capacitor Replacement",
                'complaint': "Outdoor fan humming and vibrating, needs high capacity starting capacitor",
                'status': "ASSIGNED",
                'technician': staff_users["suman"],
                'created_by': staff_users["admin"],
                'created_at': t_10_42 - timedelta(minutes=40),
                'service_charge': Decimal('1200.00'),
                'total_amount': Decimal('1200.00'),
                'payment_status': 'PENDING',
            }
        )

        # 2 NEW jobs:
        j_new1, _ = ServiceJob.objects.get_or_create(
            business=business,
            job_number="JOB-2026-00487",
            defaults={
                'customer': customers["9855000005"],
                'ac_brand_name': "LG",
                'ac_type_name': "Split AC",
                'ac_capacity_name': "2.0 Ton",
                'service_type': "Installation",
                'complaint': "Customer relocated office; request for outdoor unit uninstallation & reinstallation",
                'status': "NEW",
                'technician': None,
                'created_by': staff_users["admin"],
                'created_at': t_10_42 - timedelta(minutes=15),
                'service_charge': Decimal('3500.00'),
                'total_amount': Decimal('3500.00'),
                'payment_status': 'PENDING',
            }
        )
        j_new2, _ = ServiceJob.objects.get_or_create(
            business=business,
            job_number="JOB-2026-00488",
            defaults={
                'customer': customers["9845000006"],
                'ac_brand_name': "Daikin",
                'ac_type_name': "Split AC",
                'ac_capacity_name': "1.5 Ton",
                'service_type': "AC Not Cooling",
                'complaint': "Remote not responding, display flashing green light",
                'status': "NEW",
                'technician': None,
                'created_by': staff_users["admin"],
                'created_at': t_10_42 - timedelta(days=1),
                'service_charge': Decimal('1500.00'),
                'total_amount': Decimal('1500.00'),
                'payment_status': 'PENDING',
            }
        )

        # Seed additional historical jobs for September 2026 to achieve reports requirement:
        # Total Jobs: 84, Completed: 76, Pending: 8, Revenue: Rs. 328,500, Parts: Rs. 112,800
        # We already have 12 today's jobs (5 completed, 7 pending/in-progress).
        # We need 71 more completed jobs and 1 more pending job throughout earlier days of September 2026!
        existing_count = ServiceJob.objects.filter(created_at__year=2026, created_at__month=9).count()
        needed_hist_jobs = 84 - existing_count
        if needed_hist_jobs > 0:
            cust_list = [c for c in customers.values() if c.name != "Ram Kumar"]
            brand_list = ["LG", "Samsung", "Daikin", "Panasonic", "Gree", "Voltas"]
            tech_list = [staff_users["anup"], staff_users["raj"], staff_users["suman"], staff_users["bikash"]]
            stypes = ["AC Not Cooling", "General Service", "Gas Charging", "Capacitor Replacement", "Water Leakage"]
            
            # Target revenue remaining: 328,500 - today's revenue (48,500) = 280,000
            # Target parts remaining: 112,800 - today's parts (~26,750) = ~86,050
            avg_service = Decimal('2800.00')
            avg_parts = Decimal('1200.00')

            for i in range(1, needed_hist_jobs + 1):
                day_offset = random.randint(1, 23)
                j_date = timezone.make_aware(datetime(2026, 9, day_offset, random.randint(9, 17), random.randint(0, 59)))
                jnum = f"JOB-2026-{400 + i:05d}"
                c = random.choice(cust_list)
                b = random.choice(brand_list)
                t = random.choice(tech_list)
                st = random.choice(stypes)
                scharge = Decimal(random.choice([1500, 1800, 2200, 2500, 3000, 3500, 4000]))
                pcharge = Decimal(random.choice([0, 650, 1150, 1800, 2400, 3200]))
                tot = scharge + pcharge

                job_hist, _ = ServiceJob.objects.get_or_create(
                    business=business,
                    job_number=jnum,
                    defaults={
                        'customer': c,
                        'ac_brand_name': b,
                        'ac_type_name': "Split AC",
                        'ac_capacity_name': "1.5 Ton",
                        'service_type': st,
                        'complaint': f"{b} AC service diagnostic & maintenance",
                        'status': "COMPLETED",
                        'technician': t,
                        'created_by': staff_users["admin"],
                        'created_at': j_date,
                        'start_time': j_date,
                        'completion_time': j_date + timedelta(hours=1, minutes=30),
                        'closed_at': j_date + timedelta(hours=1, minutes=45),
                        'service_charge': scharge,
                        'parts_charge': pcharge,
                        'discount': Decimal('0.00'),
                        'total_amount': tot,
                        'payment_status': 'PAID',
                        'payment_method': random.choice(['CASH', 'ESEWA', 'FONEPAY', 'BANK']),
                        'paid_at': j_date + timedelta(hours=1, minutes=40),
                    }
                )
                Invoice.sync_from_job(job_hist)

        # 10. Generate and configure Static Payment QRs (eSewa, Fonepay, Bank)
        media_root = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), '..', 'media', 'payment_qrs')
        os.makedirs(media_root, exist_ok=True)

        esewa_path = os.path.join(media_root, 'esewa_qr.png')
        fonepay_path = os.path.join(media_root, 'fonepay_qr.png')
        bank_path = os.path.join(media_root, 'bank_qr.png')

        generate_mock_qr_image(esewa_path, "eSewa Pay (Chitwan AC)", (96, 187, 70))
        generate_mock_qr_image(fonepay_path, "Fonepay Merchant (Chitwan AC)", (208, 27, 36))
        generate_mock_qr_image(bank_path, "Nepal Bank Transfer (A/C: 012001)", (30, 58, 138))

        PaymentQR.objects.get_or_create(
            business=business,
            qr_type='ESEWA',
            defaults={
                'title': 'eSewa Direct Payment',
                'account_name': 'Chitwan Multi-Brand AC Workshop',
                'account_number': '9855012345',
                'qr_image': 'payment_qrs/esewa_qr.png',
                'is_active': True,
                'display_order': 1,
                'notes': 'Show QR to customer for direct wallet transfer'
            }
        )

        PaymentQR.objects.get_or_create(
            business=business,
            qr_type='FONEPAY',
            defaults={
                'title': 'Fonepay Merchant QR',
                'account_name': 'Chitwan Multi-Brand AC Workshop',
                'account_number': 'FONE-AC-CHITWAN-985',
                'qr_image': 'payment_qrs/fonepay_qr.png',
                'is_active': True,
                'display_order': 2,
                'notes': 'Supports all Nepali mobile banking apps'
            }
        )

        PaymentQR.objects.get_or_create(
            business=business,
            qr_type='BANK',
            defaults={
                'title': 'Nepal Bank Ltd - Corporate A/C',
                'account_name': 'Chitwan AC Service & Repair P. Ltd',
                'account_number': '01200100482910',
                'qr_image': 'payment_qrs/bank_qr.png',
                'is_active': True,
                'display_order': 3,
                'notes': 'Branch: Bharatpur Main Branch'
            }
        )

        # 11. Initial Activity Logs (from prompt section 21)
        ActivityLog.objects.all().delete()
        logs_to_seed = [
            (staff_users["anup"], "Anup Pokhrel added LG Capacitor ×1", "STOCK_UPDATE", "JOB-2026-00482", "Added LG Capacitor 45µF (Rs. 650) to JOB-2026-00482", t_10_42 + timedelta(minutes=9)),
            (staff_users["anup"], "Anup Pokhrel started JOB-00482", "JOB_UPDATE", "JOB-2026-00482", "Changed status from ASSIGNED to IN_PROGRESS", t_10_42),
            (staff_users["raj"], "Raj Thapa completed JOB-00481", "JOB_UPDATE", "JOB-2026-00481", "Completed General Service for Sita Sharma (Rs. 1,800)", t_10_18),
            (staff_users["suman"], "Suman KC marked JOB-00480 Waiting for Parts", "JOB_UPDATE", "JOB-2026-00480", "Waiting for replacement Daikin Inverter PCB Board", t_09_10 + timedelta(minutes=55)),
            (staff_users["admin"], "Admin added Samsung PCB Board", "STOCK_UPDATE", "", "Inventory item added with min stock 3", t_09_10 + timedelta(minutes=20)),
            (staff_users["admin"], "Admin updated Fonepay QR", "SYSTEM", "", "Merchant payment QR configuration saved", t_09_10 + timedelta(minutes=5)),
        ]

        for user, act_text, act_type, jref, dtl, ts in logs_to_seed:
            log = ActivityLog.objects.create(
                business=business,
                user=user,
                action=act_text,
                action_type=act_type,
                job_reference=jref,
                details=dtl,
            )
            # update timestamp manually
            ActivityLog.objects.filter(id=log.id).update(created_at=ts)

        # 12. Create stock transaction for JOB-00482
        StockTransaction.objects.get_or_create(
            item=items["LG Capacitor 45µF"],
            transaction_type='SERVICE_USAGE',
            job_reference='JOB-2026-00482',
            defaults={
                'service_job': job_482,
                'quantity_change': Decimal('-1.00'),
                'balance_after': Decimal('4.00'),
                'unit_price': Decimal('650.00'),
                'performed_by': staff_users["anup"],
                'notes': 'Used on LG Split AC repair for Ram Kumar'
            }
        )
        StockTransaction.objects.get_or_create(
            item=items["Copper Pipe 1/4\""],
            transaction_type='SERVICE_USAGE',
            job_reference='JOB-2026-00482',
            defaults={
                'service_job': job_482,
                'quantity_change': Decimal('-2.00'),
                'balance_after': Decimal('8.00'),
                'unit_price': Decimal('250.00'),
                'performed_by': staff_users["anup"],
                'notes': 'Copper piping section replaced on JOB-2026-00482'
            }
        )

        # 13. Ensure all ServiceJobs have their direct Brand relationship linked
        for j in ServiceJob.objects.all():
            if not j.brand and j.ac_brand_name:
                b_match = brands.get(j.ac_brand_name)
                if b_match:
                    j.brand = b_match
                    j.save(update_fields=['brand'])

        # 14. Ensure all StockTransactions have service_job linked if job_reference exists
        for tx in StockTransaction.objects.filter(service_job__isnull=True):
            if tx.job_reference:
                matched_job = ServiceJob.objects.filter(job_number=tx.job_reference).first()
                if matched_job:
                    tx.service_job = matched_job
                    tx.save(update_fields=['service_job'])

        self.stdout.write(self.style.SUCCESS("Successfully seeded multi-brand AC workshop database!"))

