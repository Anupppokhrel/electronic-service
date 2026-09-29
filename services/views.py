from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.db.models import Q, F, Sum
from django.utils import timezone
from decimal import Decimal
from accounts.decorators import admin_required
from core.models import Business, PaymentQR, ActivityLog
from accounts.models import StaffProfile
from customers.models import Customer
from inventory.models import Brand, InventoryItem, StockTransaction
from .models import ACUnit, ServiceJob, WorkLog, JobPart
from billing.models import Invoice, Dealer

@login_required
def job_list_view(request):
    workshop = Business.objects.first()
    status_filter = request.GET.get('status', '')
    tech_id = request.GET.get('technician', '')
    brand_id = request.GET.get('brand', '')
    appliance_filter = request.GET.get('appliance', '')
    job_type_filter = request.GET.get('job_type', '')
    payment_filter = request.GET.get('payment', '')
    warranty_filter = request.GET.get('warranty', '')
    date_filter = request.GET.get('date', '')
    search = request.GET.get('search', '').strip()

    jobs = ServiceJob.objects.filter(business=workshop).select_related('customer', 'technician', 'ac_unit', 'brand', 'warranty_dealer')

    is_tech = hasattr(request.user, 'staff_profile') and request.user.staff_profile.is_technician
    if is_tech:
        jobs = jobs.filter(technician=request.user)

    if status_filter:
        jobs = jobs.filter(status=status_filter)
    if tech_id and not is_tech:
        jobs = jobs.filter(technician_id=tech_id)
    if brand_id:
        jobs = jobs.filter(Q(brand_id=brand_id) | Q(ac_unit__brand_id=brand_id) | Q(ac_brand_name__iexact=brand_id))
    if appliance_filter:
        jobs = jobs.filter(appliance_type=appliance_filter)
    if job_type_filter:
        jobs = jobs.filter(job_type=job_type_filter)
    if payment_filter:
        jobs = jobs.filter(payment_status=payment_filter)
    if warranty_filter == '1':
        jobs = jobs.filter(is_warranty=True)
    elif warranty_filter == '0':
        jobs = jobs.filter(is_warranty=False)

    if search:
        jobs = jobs.filter(
            Q(job_number__icontains=search) |
            Q(customer__name__icontains=search) |
            Q(customer__phone__icontains=search) |
            Q(customer__address__icontains=search) |
            Q(complaint__icontains=search) |
            Q(ac_brand_name__icontains=search) |
            Q(cancel_reason__icontains=search)
        )

    today = timezone.localdate()
    if date_filter == 'today':
        jobs = jobs.filter(created_at__date=today)
    elif date_filter == 'week':
        start_week = today - timezone.timedelta(days=7)
        jobs = jobs.filter(created_at__date__gte=start_week)

    jobs = jobs.order_by('-created_at')

    # Status counts for tabs
    base_counts_qs = ServiceJob.objects.filter(business=workshop)
    if is_tech:
        base_counts_qs = base_counts_qs.filter(technician=request.user)

    counts = {
        'all': base_counts_qs.count(),
        'NEW': base_counts_qs.filter(status='NEW').count(),
        'ASSIGNED': base_counts_qs.filter(status='ASSIGNED').count(),
        'IN_PROGRESS': base_counts_qs.filter(status='IN_PROGRESS').count(),
        'WAITING_FOR_PARTS': base_counts_qs.filter(status='WAITING_FOR_PARTS').count(),
        'COMPLETED': base_counts_qs.filter(status='COMPLETED').count(),
        'CLOSED': base_counts_qs.filter(status='CLOSED').count(),
        'CANCELLED': base_counts_qs.filter(status='CANCELLED').count(),
        'WTY': base_counts_qs.filter(is_warranty=True).count(),
        'DUE': base_counts_qs.filter(is_warranty=False, payment_status='PENDING', status__in=['COMPLETED', 'CLOSED', 'PAYMENT_PENDING']).count(),
    }

    technicians = StaffProfile.objects.filter(business=workshop, role='TECHNICIAN').select_related('user')
    brands = Brand.objects.filter(business=workshop)
    dealers = Dealer.objects.filter(business=workshop, is_active=True)

    context = {
        'jobs': jobs,
        'counts': counts,
        'technicians': technicians,
        'brands': brands,
        'dealers': dealers,
        'selected_status': status_filter,
        'selected_tech': tech_id,
        'selected_brand': brand_id,
        'selected_appliance': appliance_filter,
        'selected_job_type': job_type_filter,
        'selected_payment': payment_filter,
        'selected_warranty': warranty_filter,
        'selected_date': date_filter,
        'search': search,
        'appliance_choices': ServiceJob.APPLIANCE_CHOICES,
        'job_type_choices': ServiceJob.JOB_TYPE_CHOICES,
    }
    return render(request, 'services/job_list.html', context)

@admin_required
def job_create_view(request):
    workshop = Business.objects.first()
    brands = Brand.objects.filter(business=workshop)
    technicians = StaffProfile.objects.filter(business=workshop, role='TECHNICIAN').select_related('user')

    if request.method == 'POST':
        phone = request.POST.get('phone', '').strip()
        customer_name = request.POST.get('customer_name', '').strip()
        address = request.POST.get('address', '').strip()
        landmark = request.POST.get('landmark', '').strip()

        if not phone or not customer_name:
            messages.error(request, "Customer phone number and name are required.")
            return render(request, 'services/job_form.html', {'brands': brands, 'technicians': technicians})

        # 1. Customer resolution (Prevent duplicate records)
        default_addr = workshop.address if workshop else ""
        customer, created = Customer.objects.get_or_create(
            business=workshop,
            phone=phone,
            defaults={
                'name': customer_name,
                'address': address or default_addr,
                'landmark': landmark
            }
        )
        if not created and customer_name != customer.name:
            # Update name if changed
            customer.name = customer_name
            if address:
                customer.address = address
            customer.save()

        # 2. Appliance / AC Unit resolution
        appliance_type = request.POST.get('appliance_type', 'AC')
        job_type = request.POST.get('job_type', 'GENERAL_SERVICE')
        is_warranty = 'is_warranty' in request.POST
        warranty_dealer_id = request.POST.get('warranty_dealer')
        warranty_dealer = Dealer.objects.filter(id=warranty_dealer_id, business=workshop).first() if warranty_dealer_id else None
        cancel_reason = request.POST.get('cancel_reason', '').strip()

        existing_unit_id = request.POST.get('existing_unit_id')
        ac_unit = None
        brand_id = request.POST.get('brand')
        brand_obj = Brand.objects.filter(id=brand_id).first() if brand_id else None

        if existing_unit_id:
            ac_unit = ACUnit.objects.filter(id=existing_unit_id, customer=customer).first()
            if ac_unit:
                if ac_unit.brand:
                    brand_obj = ac_unit.brand
                brand_name = ac_unit.brand.name if ac_unit.brand else "Multi-Brand"
                ac_type = ac_unit.ac_type
                capacity = ac_unit.capacity
                appliance_type = ac_unit.appliance_type
            else:
                brand_name = brand_obj.name if brand_obj else request.POST.get('custom_brand', 'Multi-Brand')
                ac_type = request.POST.get('ac_type', 'Split AC')
                capacity = request.POST.get('capacity', '1.5 Ton')
        else:
            brand_name = brand_obj.name if brand_obj else request.POST.get('custom_brand', 'Multi-Brand')
            ac_type = request.POST.get('ac_type', 'Split AC')
            capacity = request.POST.get('capacity', '1.5 Ton')
            model_number = request.POST.get('model_number', '').strip()
            serial_number = request.POST.get('serial_number', '').strip()
            location_notes = request.POST.get('location_notes', '').strip()

            # Find or create appliance unit for this customer
            ac_unit = ACUnit.objects.filter(
                customer=customer,
                appliance_type=appliance_type,
                brand=brand_obj,
                ac_type=ac_type,
                capacity=capacity
            ).first()

            if not ac_unit and brand_obj:
                ac_unit = ACUnit.objects.create(
                    customer=customer,
                    appliance_type=appliance_type,
                    brand=brand_obj,
                    ac_type=ac_type,
                    capacity=capacity,
                    model_number=model_number,
                    serial_number=serial_number,
                    location_notes=location_notes
                )

        # 3. Create Service Job
        service_type = request.POST.get('service_type', 'General Service')
        complaint = request.POST.get('complaint', '').strip()
        technician_id = request.POST.get('technician')
        tech_user = None
        if technician_id:
            from django.contrib.auth.models import User
            tech_user = User.objects.filter(id=technician_id).first()

        service_charge = Decimal(request.POST.get('service_charge', '1500') or '0')
        priority = request.POST.get('priority', 'NORMAL')

        initial_status = 'ASSIGNED' if tech_user else 'NEW'
        job_number = ServiceJob.generate_next_job_number(business=workshop)

        if is_warranty:
            total_amount = Decimal('0.00')
            dealer_claim_amount = service_charge
            payment_status = 'WARRANTY'
            payment_method = 'DEALER_CLAIM'
        else:
            total_amount = service_charge
            dealer_claim_amount = Decimal('0.00')
            payment_status = 'PENDING'
            payment_method = 'CASH'

        job = ServiceJob.objects.create(
            business=workshop,
            job_number=job_number,
            customer=customer,
            appliance_type=appliance_type,
            job_type=job_type,
            brand=brand_obj,
            ac_unit=ac_unit,
            ac_brand_name=brand_name,
            ac_type_name=ac_type,
            ac_capacity_name=capacity,
            service_type=service_type,
            complaint=complaint,
            status=initial_status,
            priority=priority,
            technician=tech_user,
            created_by=request.user,
            service_charge=service_charge,
            parts_charge=Decimal('0.00'),
            discount=Decimal('0.00'),
            total_amount=total_amount,
            is_warranty=is_warranty,
            warranty_dealer=warranty_dealer,
            dealer_claim_status='PENDING' if is_warranty else 'PENDING',
            dealer_claim_amount=dealer_claim_amount,
            cancel_reason=cancel_reason,
            payment_status=payment_status,
            payment_method=payment_method
        )

        # Sync invoice
        Invoice.sync_from_job(job)

        # Update staff status to WORKING if assigned
        if tech_user and hasattr(tech_user, 'staff_profile'):
            tech_user.staff_profile.status = 'WORKING'
            tech_user.staff_profile.save()

        ActivityLog.objects.create(
            business=workshop,
            user=request.user,
            action=f"Created {job.job_number} for {customer.name} ({job.get_appliance_type_display()} - {brand_name})",
            action_type="JOB_UPDATE",
            job_reference=job.job_number,
            details=f"Job Type: {job.get_job_type_display()}, Assigned to {tech_user.get_full_name() if tech_user else 'Unassigned'}"
        )

        messages.success(request, f"Service Job {job.job_number} created successfully! You can now send the job details to technician via WhatsApp below.")
        return redirect('services:job_detail', pk=job.pk)

    dealers = Dealer.objects.filter(business=workshop, is_active=True)
    customer_id = request.GET.get('customer_id')
    customer_phone = request.GET.get('customer_phone') or request.GET.get('phone', '')
    preselected_customer = None
    if customer_id:
        preselected_customer = Customer.objects.filter(id=customer_id, business=workshop).first()
    elif customer_phone:
        preselected_customer = Customer.objects.filter(phone=customer_phone, business=workshop).first()

    unit_id = request.GET.get('unit_id')
    preselected_unit = None
    if unit_id:
        preselected_unit = ACUnit.objects.filter(id=unit_id).first()
        if preselected_unit and not preselected_customer:
            preselected_customer = preselected_unit.customer

    selected_brand_id = request.GET.get('brand')
    selected_dealer_id = request.GET.get('warranty_dealer')
    selected_tech_id = request.GET.get('technician')

    return render(request, 'services/job_form.html', {
        'brands': brands,
        'technicians': technicians,
        'dealers': dealers,
        'appliance_choices': ServiceJob.APPLIANCE_CHOICES,
        'job_type_choices': ServiceJob.JOB_TYPE_CHOICES,
        'preselected_customer': preselected_customer,
        'preselected_unit': preselected_unit,
        'selected_brand_id': selected_brand_id,
        'selected_dealer_id': selected_dealer_id,
        'selected_tech_id': selected_tech_id,
        'customer_phone': customer_phone,
    })

@login_required
def job_detail_view(request, pk):
    job = get_object_or_404(
        ServiceJob.objects.select_related('customer', 'technician', 'ac_unit', 'brand', 'created_by'),
        pk=pk
    )
    workshop = job.business

    # Technician access control: technicians can only access jobs assigned to them
    if hasattr(request.user, 'staff_profile') and request.user.staff_profile.is_technician:
        if job.technician != request.user:
            messages.error(request, "Access restricted: You can only view and service jobs assigned to you.")
            return redirect('services:technician_view')

    work_logs = job.work_logs.select_related('technician').order_by('created_at')
    parts_used = job.parts_used.select_related('inventory_item', 'added_by').order_by('added_at')

    # Ensure linked Invoice is always safely synced and present
    invoice = getattr(job, 'invoice', None)
    if not invoice:
        try:
            invoice = Invoice.sync_from_job(job)
        except Exception:
            invoice = None

    # Spare parts strictly filtered by the selected company (brand) and selected appliance
    brand_obj = job.brand or (job.ac_unit.brand if job.ac_unit else None)
    brand_name = job.ac_brand_name or (brand_obj.name if brand_obj else "")
    appliance_type = job.appliance_type or (job.ac_unit.appliance_type if job.ac_unit else "AC")

    is_generic_brand = False
    if brand_obj and (brand_obj.is_common or brand_obj.name.lower() == 'common'):
        is_generic_brand = True
    elif not brand_obj and (not brand_name or brand_name.lower() in ['common', 'multi-brand', 'generic']):
        is_generic_brand = True

    # 1. Dedicated brand parts for this specific company AND device
    brand_q = Q()
    if brand_obj:
        brand_q |= Q(brand=brand_obj)
    if brand_name:
        brand_q |= Q(brand__name__iexact=brand_name)

    if not is_generic_brand and (brand_obj or brand_name):
        brand_parts = InventoryItem.objects.filter(
            business=workshop,
            appliance_type=appliance_type
        ).filter(brand_q).order_by('part_name')
    else:
        brand_parts = InventoryItem.objects.none()

    # 2. Universal / common consumables relevant to this appliance
    common_parts = InventoryItem.objects.filter(
        business=workshop
    ).filter(
        Q(inventory_type='COMMON') | Q(brand__is_common=True) | Q(brand__name__iexact='Common')
    ).filter(
        Q(appliance_type=appliance_type) | Q(appliance_type='ALL')
    ).order_by('part_name')

    # Available parts: strictly brand parts by default if brand is specified, or common parts if generic
    if brand_parts.exists():
        available_parts = brand_parts
    elif is_generic_brand:
        available_parts = common_parts
    else:
        available_parts = InventoryItem.objects.none()

    # Static Payment QR codes
    payment_qrs = PaymentQR.objects.filter(business=workshop, is_active=True).order_by('display_order')

    # Technicians list for re-assignment
    technicians = StaffProfile.objects.filter(business=workshop, role='TECHNICIAN').select_related('user')

    # WhatsApp pre-formatted job dispatch
    tech_phone = ""
    tech_user = job.technician
    if tech_user and hasattr(tech_user, 'staff_profile') and tech_user.staff_profile.phone:
        raw_phone = tech_user.staff_profile.phone.strip().replace(" ", "").replace("-", "").replace("+", "")
        if len(raw_phone) == 10 and raw_phone.startswith('9'):
            tech_phone = f"977{raw_phone}"
        else:
            tech_phone = raw_phone

    import urllib.parse
    brand_label = job.ac_brand_name or (job.brand.name if job.brand else "General")
    warranty_label = "Warranty Claim" if job.is_warranty else "Customer Paid"
    landmark_str = f" (Near {job.customer.landmark})" if job.customer.landmark else ""

    wa_lines = [
        f"🔧 *JOB ASSIGNMENT - {job.job_number}*",
        f"━━━━━━━━━━━━━━━━━━━━",
        f"👤 *Customer:* {job.customer.name}",
        f"📞 *Phone:* {job.customer.phone}",
        f"📍 *Location:* {job.customer.address or 'Workshop / On-site'}{landmark_str}",
        f"━━━━━━━━━━━━━━━━━━━━",
        f"❄️ *Appliance:* {job.get_appliance_type_display()} ({brand_label})",
        f"🛠️ *Job Type:* {job.get_job_type_display()}",
        f"⚠️ *Complaint:* {job.complaint or 'Inspection / Service'}",
        f"━━━━━━━━━━━━━━━━━━━━",
        f"💰 *Fee:* Rs. {job.service_charge:,.0f} ({warranty_label})",
        f"📅 *Date:* {job.created_at.strftime('%Y-%m-%d')}",
    ]
    whatsapp_text = "\n".join(wa_lines)
    whatsapp_url = f"https://api.whatsapp.com/send?text={urllib.parse.quote(whatsapp_text)}"
    if tech_phone:
        whatsapp_url = f"https://api.whatsapp.com/send?phone={tech_phone}&text={urllib.parse.quote(whatsapp_text)}"

    context = {
        'job': job,
        'invoice': invoice,
        'work_logs': work_logs,
        'parts_used': parts_used,
        'available_parts': available_parts,
        'brand_parts': brand_parts,
        'common_parts': common_parts,
        'brand_name': brand_name,
        'brand_obj': brand_obj,
        'is_generic_brand': is_generic_brand,
        'payment_qrs': payment_qrs,
        'technicians': technicians,
        'dealers': Dealer.objects.filter(business=workshop, is_active=True),
        'whatsapp_text': whatsapp_text,
        'whatsapp_url': whatsapp_url,
        'tech_phone': tech_phone,
    }
    return render(request, 'services/job_detail.html', context)

@login_required
def job_technician_view(request):
    """Technician Mobile-Friendly Work Hub"""
    workshop = Business.objects.first()
    user = request.user
    
    # If admin viewing, show all active jobs or allow switching
    if user.staff_profile.is_admin:
        tech_id = request.GET.get('tech')
        if tech_id:
            user_to_show = get_object_or_404(StaffProfile, id=tech_id).user
        else:
            user_to_show = user
    else:
        user_to_show = user

    my_in_progress = ServiceJob.objects.filter(
        business=workshop,
        technician=user_to_show,
        status='IN_PROGRESS'
    ).select_related('customer', 'ac_unit').order_by('-start_time')

    my_assigned = ServiceJob.objects.filter(
        business=workshop,
        technician=user_to_show,
        status='ASSIGNED'
    ).select_related('customer', 'ac_unit').order_by('-created_at')

    my_waiting = ServiceJob.objects.filter(
        business=workshop,
        technician=user_to_show,
        status='WAITING_FOR_PARTS'
    ).select_related('customer', 'ac_unit').order_by('-created_at')

    my_completed_today = ServiceJob.objects.filter(
        business=workshop,
        technician=user_to_show,
        status__in=['COMPLETED', 'CLOSED'],
        created_at__date=timezone.localdate()
    ).select_related('customer').order_by('-completion_time')

    all_technicians = StaffProfile.objects.filter(business=workshop, role='TECHNICIAN').select_related('user')
    payment_qrs = PaymentQR.objects.filter(business=workshop, is_active=True).order_by('display_order')

    context = {
        'tech_user': user_to_show,
        'my_in_progress': my_in_progress,
        'my_assigned': my_assigned,
        'my_waiting': my_waiting,
        'my_completed_today': my_completed_today,
        'all_technicians': all_technicians,
        'payment_qrs': payment_qrs,
    }
    return render(request, 'services/technician_view.html', context)

@login_required
def job_update_status_view(request, pk):
    job = get_object_or_404(ServiceJob, pk=pk)
    is_tech = hasattr(request.user, 'staff_profile') and request.user.staff_profile.is_technician
    if is_tech and job.technician != request.user:
        messages.error(request, "Access restricted: You can only update jobs assigned to you.")
        return redirect('services:technician_view')

    if request.method == 'POST':
        action = request.POST.get('action')
        now = timezone.now()

        if is_tech and action in ['CANCEL_JOB', 'CLOSE_JOB', 'ASSIGN_TECH']:
            messages.error(request, "Permission denied: Only the workshop owner/admin can cancel, close, or reassign jobs.")
            return redirect('services:job_detail', pk=pk)

        if action == 'START_WORK':
            job.status = 'IN_PROGRESS'
            if not job.start_time:
                job.start_time = now
            if not job.technician:
                job.technician = request.user
            job.save()

            if job.technician and hasattr(job.technician, 'staff_profile'):
                job.technician.staff_profile.status = 'WORKING'
                job.technician.staff_profile.save()

            ActivityLog.objects.create(
                business=job.business,
                user=request.user,
                action=f"{request.user.get_full_name() or request.user.username} started {job.job_number}",
                action_type="JOB_UPDATE",
                job_reference=job.job_number
            )
            messages.success(request, f"Job {job.job_number} started! Status is now IN PROGRESS.")

        elif action == 'WAIT_FOR_PARTS':
            reason = request.POST.get('reason', '').strip()
            job.status = 'WAITING_FOR_PARTS'
            job.save()

            log_desc = f"Work paused: Waiting for Parts ({reason})" if reason else "Work paused: Waiting for required spare parts"
            WorkLog.objects.create(job=job, technician=request.user, description=log_desc)

            ActivityLog.objects.create(
                business=job.business,
                user=request.user,
                action=f"{request.user.get_full_name()} marked {job.job_number} Waiting for Parts",
                action_type="JOB_UPDATE",
                job_reference=job.job_number,
                details=reason
            )
            messages.warning(request, f"Job {job.job_number} marked as WAITING FOR PARTS.")

        elif action == 'RESUME_WORK':
            job.status = 'IN_PROGRESS'
            job.save()
            WorkLog.objects.create(job=job, technician=request.user, description="Work resumed after parts received")
            ActivityLog.objects.create(
                business=job.business,
                user=request.user,
                action=f"{request.user.get_full_name()} resumed {job.job_number}",
                action_type="JOB_UPDATE",
                job_reference=job.job_number
            )
            messages.success(request, f"Job {job.job_number} resumed! Status is IN PROGRESS.")

        elif action == 'COMPLETE_WORK':
            job.status = 'COMPLETED'
            if not job.completion_time:
                job.completion_time = now
            job.save()

            # Check if technician has other active jobs
            if job.technician and hasattr(job.technician, 'staff_profile'):
                other_active = ServiceJob.objects.filter(
                    technician=job.technician,
                    status='IN_PROGRESS'
                ).exclude(id=job.id).exists()
                if not other_active:
                    job.technician.staff_profile.status = 'AVAILABLE'
                    job.technician.staff_profile.save()

            ActivityLog.objects.create(
                business=job.business,
                user=request.user,
                action=f"{request.user.get_full_name()} completed {job.job_number}",
                action_type="JOB_UPDATE",
                job_reference=job.job_number
            )
            messages.success(request, f"Job {job.job_number} marked as COMPLETED!")

        elif action == 'CLOSE_JOB':
            job.status = 'CLOSED'
            job.closed_at = now
            job.save()
            ActivityLog.objects.create(
                business=job.business,
                user=request.user,
                action=f"Closed service job {job.job_number}",
                action_type="JOB_UPDATE",
                job_reference=job.job_number
            )
            messages.info(request, f"Job {job.job_number} closed.")

        elif action == 'CANCEL_JOB':
            cancel_reason = request.POST.get('cancel_reason', '').strip()
            job.status = 'CANCELLED'
            job.cancel_reason = cancel_reason
            job.closed_at = now
            job.save()
            WorkLog.objects.create(job=job, technician=request.user, description=f"Job Cancelled / Aborted: {cancel_reason or 'No reason provided'}")
            ActivityLog.objects.create(
                business=job.business,
                user=request.user,
                action=f"Cancelled {job.job_number}",
                action_type="JOB_UPDATE",
                job_reference=job.job_number,
                details=cancel_reason
            )
            messages.warning(request, f"Job {job.job_number} marked as CANCELLED.")

        elif action == 'ASSIGN_TECH':
            tech_id = request.POST.get('technician')
            if tech_id:
                from django.contrib.auth.models import User
                new_tech = get_object_or_404(User, id=tech_id)
                job.technician = new_tech
                if job.status == 'NEW':
                    job.status = 'ASSIGNED'
                job.save()
                ActivityLog.objects.create(
                    business=job.business,
                    user=request.user,
                    action=f"Assigned {new_tech.get_full_name()} to {job.job_number}",
                    action_type="JOB_UPDATE",
                    job_reference=job.job_number
                )
                messages.success(request, f"Assigned to {new_tech.get_full_name()}.")

    # Return to caller or job detail
    next_url = request.POST.get('next') or request.META.get('HTTP_REFERER')
    return redirect(next_url or 'services:job_detail', pk=pk)

@login_required
def job_add_work_log_view(request, pk):
    job = get_object_or_404(ServiceJob, pk=pk)
    if hasattr(request.user, 'staff_profile') and request.user.staff_profile.is_technician:
        if job.technician != request.user:
            messages.error(request, "Access restricted: You can only log work on jobs assigned to you.")
            return redirect('services:technician_view')

    if request.method == 'POST':
        description = request.POST.get('description', '').strip()
        if description:
            WorkLog.objects.create(
                job=job,
                technician=request.user,
                description=description
            )
            ActivityLog.objects.create(
                business=job.business,
                user=request.user,
                action=f"Logged work on {job.job_number}: {description[:50]}",
                action_type="JOB_UPDATE",
                job_reference=job.job_number
            )
            messages.success(request, "Work log recorded.")
        else:
            messages.error(request, "Please enter work description.")

    return redirect('services:job_detail', pk=pk)

@login_required
def job_add_part_view(request, pk):
    job = get_object_or_404(ServiceJob, pk=pk)
    if hasattr(request.user, 'staff_profile') and request.user.staff_profile.is_technician:
        if job.technician != request.user:
            messages.error(request, "Access restricted: You can only add parts to jobs assigned to you.")
            return redirect('services:technician_view')

    if request.method == 'POST':
        item_id = request.POST.get('inventory_item')
        qty = Decimal(request.POST.get('quantity', '1') or '1')

        if not item_id or qty <= 0:
            messages.error(request, "Invalid item or quantity.")
            return redirect('services:job_detail', pk=pk)

        with transaction.atomic():
            item = get_object_or_404(InventoryItem.objects.select_for_update(), id=item_id, business=job.business)

            if item.quantity < qty:
                messages.error(
                    request,
                    f"Insufficient stock for {item.part_name}. Available: {item.stock_display}, Requested: {qty} {item.unit}."
                )
                return redirect('services:job_detail', pk=pk)

            # Deduct stock safely
            item.quantity -= qty
            item.save()

            # Create StockTransaction
            StockTransaction.objects.create(
                item=item,
                transaction_type='SERVICE_USAGE',
                quantity_change=-qty,
                balance_after=item.quantity,
                unit_price=item.selling_price,
                service_job=job,
                job_reference=job.job_number,
                performed_by=request.user,
                notes=f"Used in {job.job_number} ({job.customer.name})"
            )

            # Create JobPart record
            unit_price = Decimal(request.POST.get('unit_price') or str(item.selling_price))
            JobPart.objects.create(
                job=job,
                inventory_item=item,
                quantity=qty,
                unit_price=unit_price,
                added_by=request.user
            )

            # Recalculate job totals and update invoice
            job.recalculate_totals()

            ActivityLog.objects.create(
                business=job.business,
                user=request.user,
                action=f"{request.user.get_full_name()} added {item.part_name} ×{qty}",
                action_type="STOCK_UPDATE",
                job_reference=job.job_number,
                details=f"Deducted {qty} {item.unit}. Remaining stock: {item.stock_display}"
            )

            if item.is_low_stock:
                messages.warning(request, f"LOW STOCK ALERT: {item.part_name} has only {item.stock_display} remaining!")
            else:
                messages.success(request, f"Added {qty} {item.unit} of {item.part_name} to {job.job_number}.")

    return redirect('services:job_detail', pk=pk)

@login_required
def job_remove_part_view(request, pk, part_id):
    job = get_object_or_404(ServiceJob, pk=pk)
    if hasattr(request.user, 'staff_profile') and request.user.staff_profile.is_technician:
        if job.technician != request.user:
            messages.error(request, "Access restricted: You can only remove parts from jobs assigned to you.")
            return redirect('services:technician_view')

    part = get_object_or_404(JobPart, pk=part_id, job=job)

    with transaction.atomic():
        item = get_object_or_404(InventoryItem.objects.select_for_update(), id=part.inventory_item_id)
        # Restore stock
        item.quantity += part.quantity
        item.save()

        # Create return transaction
        StockTransaction.objects.create(
            item=item,
            transaction_type='RETURN',
            quantity_change=part.quantity,
            balance_after=item.quantity,
            unit_price=part.unit_price,
            service_job=job,
            job_reference=job.job_number,
            performed_by=request.user,
            notes=f"Returned from {job.job_number}"
        )

        part_name = item.part_name
        part_qty = part.quantity
        part_unit = item.unit
        part.delete()

        job.recalculate_totals()

        ActivityLog.objects.create(
            business=job.business,
            user=request.user,
            action=f"Removed {part_name} ×{part_qty} from {job.job_number} (stock restored)",
            action_type="STOCK_UPDATE",
            job_reference=job.job_number
        )

    messages.info(request, f"Removed {part_name} and restored {part_qty} {part_unit} back to inventory.")
    return redirect('services:job_detail', pk=pk)

@admin_required
def job_update_financials_view(request, pk):
    job = get_object_or_404(ServiceJob, pk=pk)
    if request.method == 'POST':
        service_charge = Decimal(request.POST.get('service_charge', '0') or '0')
        discount = Decimal(request.POST.get('discount', '0') or '0')

        job.service_charge = service_charge
        job.discount = discount
        job.recalculate_totals()

        messages.success(request, "Service charges updated successfully.")

    return redirect('services:job_detail', pk=pk)

@admin_required
def job_record_payment_view(request, pk):
    job = get_object_or_404(ServiceJob, pk=pk)
    if request.method == 'POST':
        payment_method = request.POST.get('payment_method', 'CASH')
        payment_reference = request.POST.get('payment_reference', '').strip()
        mark_closed = 'mark_closed' in request.POST

        job.payment_status = 'PAID'
        job.payment_method = payment_method
        job.payment_reference = payment_reference
        job.paid_at = timezone.now()

        if mark_closed:
            job.status = 'CLOSED'
            job.closed_at = timezone.now()
        elif job.status in ['NEW', 'ASSIGNED', 'IN_PROGRESS', 'WAITING_FOR_PARTS']:
            job.status = 'COMPLETED'
            job.completion_time = timezone.now()

        job.save()
        Invoice.sync_from_job(job)

        ActivityLog.objects.create(
            business=job.business,
            user=request.user,
            action=f"Payment recorded: Rs. {job.total_amount} via {payment_method} for {job.job_number}",
            action_type="PAYMENT",
            job_reference=job.job_number,
            details=f"Reference: {payment_reference}"
        )

        messages.success(request, f"Payment of Rs. {job.total_amount} recorded via {payment_method}!")

    return redirect('services:job_detail', pk=pk)
