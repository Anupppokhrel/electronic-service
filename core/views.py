from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, F, Sum, Count
from django.utils import timezone
from decimal import Decimal
from accounts.decorators import admin_required
from core.models import Business, PaymentQR, ActivityLog
from accounts.models import StaffProfile
from customers.models import Customer
from inventory.models import InventoryItem, Brand
from services.models import ServiceJob
from billing.models import Invoice

@login_required
def dashboard_view(request):
    workshop = Business.objects.first()
    today = timezone.localdate()

    # Today's Jobs
    today_jobs = ServiceJob.objects.filter(business=workshop, created_at__date=today).order_by('-created_at')
    
    # Counts
    total_today_jobs = today_jobs.count()
    new_jobs_count = ServiceJob.objects.filter(business=workshop, status='NEW').count()
    assigned_jobs_count = today_jobs.filter(status='ASSIGNED').count()
    in_progress_jobs_count = today_jobs.filter(status='IN_PROGRESS').count()
    waiting_parts_jobs_count = today_jobs.filter(status='WAITING_FOR_PARTS').count()
    completed_jobs_count = today_jobs.filter(status__in=['COMPLETED', 'CLOSED']).count()

    # Today's Revenue (from completed/paid jobs today)
    today_revenue = ServiceJob.objects.filter(
        business=workshop,
        created_at__date=today,
        status__in=['COMPLETED', 'CLOSED'],
        payment_status='PAID'
    ).aggregate(total=Sum('total_amount'))['total'] or 0

    # Low Stock Items
    low_stock_items = InventoryItem.objects.filter(
        business=workshop,
        quantity__lte=F('minimum_stock')
    ).select_related('brand', 'category')
    low_stock_count = low_stock_items.count()

    # Staff Members
    staff_members = StaffProfile.objects.filter(
        business=workshop,
        role='TECHNICIAN'
    ).select_related('user').order_by('user__first_name')

    # Staff Activities (recent)
    recent_activities = ActivityLog.objects.filter(business=workshop)[:10]

    # Quick highlight jobs (specifically the 4 requested in prompt section 6)
    highlight_jobs = today_jobs[:6]

    # Customer Due (Udharo / Unpaid)
    total_due_amount = ServiceJob.objects.filter(
        business=workshop,
        is_warranty=False,
        payment_status='PENDING',
        status__in=['COMPLETED', 'CLOSED', 'PAYMENT_PENDING']
    ).aggregate(total=Sum('total_amount'))['total'] or 0

    due_jobs = ServiceJob.objects.filter(
        business=workshop,
        is_warranty=False,
        payment_status='PENDING',
        status__in=['COMPLETED', 'CLOSED', 'PAYMENT_PENDING']
    ).select_related('customer').order_by('-created_at')[:5]

    # Dealer Warranty Claims (WTY)
    pending_warranty_claims_amount = ServiceJob.objects.filter(
        business=workshop,
        is_warranty=True,
        dealer_claim_status__in=['PENDING', 'SUBMITTED']
    ).aggregate(total=Sum('dealer_claim_amount'))['total'] or 0

    warranty_jobs_count = ServiceJob.objects.filter(business=workshop, is_warranty=True).count()

    # Appliance Breakdown
    appliance_counts = {
        'AC': ServiceJob.objects.filter(business=workshop, appliance_type='AC').count(),
        'REF': ServiceJob.objects.filter(business=workshop, appliance_type='REFRIGERATOR').count(),
        'WM': ServiceJob.objects.filter(business=workshop, appliance_type='WASHING_MACHINE').count(),
        'COOLER': ServiceJob.objects.filter(business=workshop, appliance_type='COOLER').count(),
    }

    context = {
        'workshop': workshop,
        'today': today,
        'total_today_jobs': total_today_jobs,
        'new_jobs_count': new_jobs_count,
        'assigned_jobs_count': assigned_jobs_count,
        'in_progress_jobs_count': in_progress_jobs_count,
        'waiting_parts_jobs_count': waiting_parts_jobs_count,
        'completed_jobs_count': completed_jobs_count,
        'today_revenue': today_revenue,
        'low_stock_items': low_stock_items,
        'low_stock_count': low_stock_count,
        'staff_members': staff_members,
        'recent_activities': recent_activities,
        'highlight_jobs': highlight_jobs,
        'total_due_amount': total_due_amount,
        'due_jobs': due_jobs,
        'pending_warranty_claims_amount': pending_warranty_claims_amount,
        'warranty_jobs_count': warranty_jobs_count,
        'appliance_counts': appliance_counts,
    }
    return render(request, 'core/dashboard.html', context)

@login_required
def global_search_view(request):
    query = request.GET.get('q', '').strip()
    workshop = Business.objects.first()

    customers = []
    jobs = []
    invoices = []
    inventory_items = []
    staff_members = []

    is_tech = hasattr(request.user, 'staff_profile') and request.user.staff_profile.is_technician

    if query:
        if is_tech:
            # Technicians are strictly restricted to searching ONLY their assigned jobs and inventory availability
            jobs = ServiceJob.objects.filter(
                business=workshop,
                technician=request.user
            ).filter(
                Q(job_number__icontains=query) |
                Q(customer__name__icontains=query) |
                Q(complaint__icontains=query) |
                Q(ac_brand_name__icontains=query)
            ).select_related('customer', 'technician')[:15]

            inventory_items = InventoryItem.objects.filter(
                business=workshop
            ).filter(
                Q(part_name__icontains=query) |
                Q(part_code__icontains=query) |
                Q(brand__name__icontains=query)
            ).select_related('brand')[:15]
        else:
            # Search Customers (Name, Phone, Address)
            customers = Customer.objects.filter(
                business=workshop
            ).filter(
                Q(name__icontains=query) | Q(phone__icontains=query) | Q(address__icontains=query)
            )[:15]

            # Search Jobs (Job Number, Complaint, Service Type, AC Brand)
            jobs = ServiceJob.objects.filter(
                business=workshop
            ).filter(
                Q(job_number__icontains=query) |
                Q(customer__name__icontains=query) |
                Q(customer__phone__icontains=query) |
                Q(complaint__icontains=query) |
                Q(ac_brand_name__icontains=query) |
                Q(technician__first_name__icontains=query) |
                Q(technician__last_name__icontains=query)
            ).select_related('customer', 'technician')[:15]

            # Search Invoices (Invoice Number)
            invoices = Invoice.objects.filter(
                business=workshop
            ).filter(
                Q(invoice_number__icontains=query) |
                Q(job__job_number__icontains=query) |
                Q(customer__name__icontains=query) |
                Q(customer__phone__icontains=query)
            ).select_related('customer', 'job')[:15]

            # Search Inventory (Part Name, Part Code, Brand Name)
            inventory_items = InventoryItem.objects.filter(
                business=workshop
            ).filter(
                Q(part_name__icontains=query) |
                Q(part_code__icontains=query) |
                Q(brand__name__icontains=query) |
                Q(supplier__icontains=query)
            ).select_related('brand')[:15]

            # Search Staff
            staff_members = StaffProfile.objects.filter(
                business=workshop
            ).filter(
                Q(user__first_name__icontains=query) |
                Q(user__last_name__icontains=query) |
                Q(phone__icontains=query)
            ).select_related('user')[:10]

    context = {
        'query': query,
        'customers': customers,
        'jobs': jobs,
        'invoices': invoices,
        'inventory_items': inventory_items,
        'staff_members': staff_members,
        'total_results': len(customers) + len(jobs) + len(invoices) + len(inventory_items) + len(staff_members),
    }
    return render(request, 'core/search_results.html', context)

@admin_required
def settings_view(request):
    workshop = Business.objects.first()

    if request.method == 'POST':
        workshop.name = request.POST.get('name', workshop.name)
        workshop.tagline = request.POST.get('tagline', workshop.tagline)
        workshop.owner_name = request.POST.get('owner_name', workshop.owner_name)
        workshop.phone = request.POST.get('phone', workshop.phone)
        workshop.alt_phone = request.POST.get('alt_phone', workshop.alt_phone)
        workshop.email = request.POST.get('email', workshop.email)
        workshop.address = request.POST.get('address', workshop.address)
        workshop.pan_number = request.POST.get('pan_number', workshop.pan_number)
        workshop.currency_symbol = request.POST.get('currency_symbol', workshop.currency_symbol)
        workshop.save()

        ActivityLog.objects.create(
            business=workshop,
            user=request.user,
            action="Updated Workshop Business Settings",
            action_type="SYSTEM",
            details=f"Updated settings for {workshop.name}"
        )
        messages.success(request, "Workshop settings updated successfully.")
        return redirect('core:settings')

    context = {'workshop': workshop}
    return render(request, 'core/settings.html', context)

@admin_required
def payment_qr_settings_view(request):
    workshop = Business.objects.first()
    qrs = PaymentQR.objects.filter(business=workshop).order_by('display_order')

    if request.method == 'POST':
        qr_id = request.POST.get('qr_id')
        qr_obj = get_object_or_404(PaymentQR, id=qr_id, business=workshop)

        qr_obj.title = request.POST.get('title', qr_obj.title)
        qr_obj.account_name = request.POST.get('account_name', qr_obj.account_name)
        qr_obj.account_number = request.POST.get('account_number', qr_obj.account_number)
        qr_obj.notes = request.POST.get('notes', qr_obj.notes)
        qr_obj.is_active = 'is_active' in request.POST

        if 'qr_image' in request.FILES:
            qr_obj.qr_image = request.FILES['qr_image']

        qr_obj.save()

        ActivityLog.objects.create(
            business=workshop,
            user=request.user,
            action=f"Updated {qr_obj.get_qr_type_display()} payment configuration",
            action_type="SYSTEM",
            details=f"Updated {qr_obj.title}"
        )
        messages.success(request, f"{qr_obj.get_qr_type_display()} updated successfully.")
        return redirect('core:payment_qr_settings')

    context = {'qrs': qrs}
    return render(request, 'core/payment_qr_settings.html', context)

@admin_required
def activity_logs_view(request):
    workshop = Business.objects.first()
    logs = ActivityLog.objects.filter(business=workshop).select_related('user')[:100]
    return render(request, 'core/activity_logs.html', {'logs': logs})
