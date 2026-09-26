from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Sum, Count
from django.utils import timezone
from decimal import Decimal
from accounts.decorators import admin_required
from core.models import Business, ActivityLog
from inventory.models import Brand
from .models import Invoice, Payment, Dealer
from services.models import ServiceJob

@admin_required
def invoice_list_view(request):
    workshop = Business.objects.first()
    search = request.GET.get('search', '').strip()
    status_filter = request.GET.get('status', '')
    tech_id = request.GET.get('technician', '')

    invoices = Invoice.objects.filter(business=workshop).select_related('customer', 'job', 'technician', 'dealer')

    if search:
        invoices = invoices.filter(
            Q(invoice_number__icontains=search) |
            Q(job__job_number__icontains=search) |
            Q(customer__name__icontains=search) |
            Q(customer__phone__icontains=search) |
            Q(customer__address__icontains=search)
        )
    if status_filter:
        invoices = invoices.filter(payment_status=status_filter)
    if tech_id:
        invoices = invoices.filter(technician_id=tech_id)

    invoices = invoices.order_by('-created_at')

    # Aggregates
    total_invoiced = invoices.filter(is_warranty=False).aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')
    total_paid = invoices.filter(payment_status='PAID').aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')
    total_due = invoices.filter(payment_status='PENDING', is_warranty=False).aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')
    total_warranty_claims = invoices.filter(is_warranty=True).aggregate(total=Sum('dealer_claim_amount'))['total'] or Decimal('0.00')

    from accounts.models import StaffProfile
    technicians = StaffProfile.objects.filter(business=workshop, role='TECHNICIAN').select_related('user')

    context = {
        'invoices': invoices,
        'search': search,
        'status_filter': status_filter,
        'selected_tech': tech_id,
        'technicians': technicians,
        'total_invoiced': total_invoiced,
        'total_paid': total_paid,
        'total_due': total_due,
        'total_warranty_claims': total_warranty_claims,
    }
    return render(request, 'billing/invoice_list.html', context)

@admin_required
def invoice_detail_view(request, pk):
    invoice = get_object_or_404(
        Invoice.objects.select_related('business', 'customer', 'job', 'technician', 'dealer'),
        pk=pk
    )
    job = invoice.job
    parts = job.parts_used.select_related('inventory_item').all()
    work_logs = job.work_logs.all()
    payments = invoice.payments.all()

    context = {
        'invoice': invoice,
        'job': job,
        'parts': parts,
        'work_logs': work_logs,
        'payments': payments,
    }
    return render(request, 'billing/invoice_detail.html', context)

@admin_required
def invoice_record_payment_view(request, pk):
    invoice = get_object_or_404(Invoice, pk=pk)
    if request.method == 'POST':
        method = request.POST.get('payment_method', 'CASH')
        reference = request.POST.get('reference', '').strip()
        notes = request.POST.get('notes', '').strip()
        amount_paid_val = Decimal(request.POST.get('amount', str(invoice.total_amount)) or '0')

        invoice.amount_paid += amount_paid_val
        if invoice.amount_paid >= invoice.total_amount:
            invoice.payment_status = 'PAID'
        invoice.payment_method = method
        invoice.paid_at = timezone.now()
        invoice.save()

        # Sync to job as well
        job = invoice.job
        if invoice.payment_status == 'PAID':
            job.payment_status = 'PAID'
            if job.status == 'COMPLETED':
                job.status = 'CLOSED'
                job.closed_at = invoice.paid_at
        job.payment_method = method
        job.payment_reference = reference
        job.paid_at = invoice.paid_at
        job.save()

        Payment.objects.create(
            invoice=invoice,
            amount=amount_paid_val,
            payment_method=method,
            reference=reference,
            received_by=request.user,
            notes=notes
        )

        ActivityLog.objects.create(
            business=invoice.business,
            user=request.user,
            action=f"Payment recorded for {invoice.invoice_number} (Rs. {amount_paid_val})",
            action_type="PAYMENT",
            job_reference=job.job_number
        )

        messages.success(request, f"Payment of Rs. {amount_paid_val} recorded for {invoice.invoice_number}.")

    # Redirect back to referring page (e.g. credit ledger or invoice detail)
    next_url = request.POST.get('next') or request.META.get('HTTP_REFERER')
    if next_url:
        return redirect(next_url)
    return redirect('billing:invoice_detail', pk=pk)

@admin_required
def credit_ledger_view(request):
    """
    Dedicated Due / Udharo Khata (Credit Ledger).
    Lists all customers with pending balances, contact numbers, addresses, and days overdue.
    """
    workshop = Business.objects.first()
    search = request.GET.get('search', '').strip()

    due_invoices = Invoice.objects.filter(
        business=workshop,
        is_warranty=False,
        payment_status='PENDING'
    ).select_related('customer', 'job', 'technician').order_by('-created_at')

    if search:
        due_invoices = due_invoices.filter(
            Q(customer__name__icontains=search) |
            Q(customer__phone__icontains=search) |
            Q(customer__address__icontains=search) |
            Q(invoice_number__icontains=search) |
            Q(job__job_number__icontains=search)
        )

    total_due_amount = due_invoices.aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')
    total_customers_count = due_invoices.values('customer').distinct().count()

    context = {
        'invoices': due_invoices,
        'search': search,
        'total_due_amount': total_due_amount,
        'total_customers_count': total_customers_count,
    }
    return render(request, 'billing/credit_ledger.html', context)

@admin_required
def warranty_claims_view(request):
    """
    Dedicated Dealer Warranty Claims Hub (WTY).
    Tracks claims to Authorized Brand Dealers (LG, Samsung, GEM, CG, etc.).
    """
    workshop = Business.objects.first()
    dealer_id = request.GET.get('dealer', '')
    status_filter = request.GET.get('status', '')
    search = request.GET.get('search', '').strip()

    claims = Invoice.objects.filter(
        business=workshop,
        is_warranty=True
    ).select_related('customer', 'job', 'dealer', 'technician').order_by('-created_at')

    if dealer_id:
        claims = claims.filter(dealer_id=dealer_id)
    if status_filter:
        claims = claims.filter(dealer_claim_status=status_filter)
    if search:
        claims = claims.filter(
            Q(dealer__name__icontains=search) |
            Q(customer__name__icontains=search) |
            Q(customer__phone__icontains=search) |
            Q(job__job_number__icontains=search) |
            Q(invoice_number__icontains=search)
        )

    total_claim_amount = claims.aggregate(total=Sum('dealer_claim_amount'))['total'] or Decimal('0.00')
    settled_claim_amount = claims.filter(dealer_claim_status='SETTLED').aggregate(total=Sum('dealer_claim_amount'))['total'] or Decimal('0.00')
    pending_claim_amount = claims.filter(dealer_claim_status__in=['PENDING', 'SUBMITTED']).aggregate(total=Sum('dealer_claim_amount'))['total'] or Decimal('0.00')

    dealers = Dealer.objects.filter(business=workshop, is_active=True)

    context = {
        'claims': claims,
        'dealers': dealers,
        'selected_dealer': dealer_id,
        'selected_status': status_filter,
        'search': search,
        'total_claim_amount': total_claim_amount,
        'settled_claim_amount': settled_claim_amount,
        'pending_claim_amount': pending_claim_amount,
    }
    return render(request, 'billing/warranty_claims.html', context)

@admin_required
def warranty_claim_update_status(request, pk):
    invoice = get_object_or_404(Invoice, pk=pk, is_warranty=True)
    if request.method == 'POST':
        new_status = request.POST.get('dealer_claim_status', 'SUBMITTED')
        invoice.dealer_claim_status = new_status
        if new_status == 'SETTLED':
            invoice.paid_at = timezone.now()
            invoice.payment_status = 'PAID'
            invoice.job.payment_status = 'PAID'
            invoice.job.paid_at = invoice.paid_at
            if invoice.job.status == 'COMPLETED':
                invoice.job.status = 'CLOSED'
                invoice.job.closed_at = invoice.paid_at
            invoice.job.save()
        invoice.save()

        # Update job field as well
        invoice.job.dealer_claim_status = new_status
        invoice.job.save(update_fields=['dealer_claim_status'])

        ActivityLog.objects.create(
            business=invoice.business,
            user=request.user,
            action=f"Warranty claim {invoice.invoice_number} updated to {new_status}",
            action_type="PAYMENT",
            job_reference=invoice.job.job_number,
            details=f"Dealer: {invoice.dealer.name if invoice.dealer else 'General'}"
        )

        messages.success(request, f"Claim {invoice.invoice_number} status updated to {new_status}.")

    return redirect('billing:warranty_claims')

@admin_required
def dealers_list_view(request):
    workshop = Business.objects.first()
    dealers = Dealer.objects.filter(business=workshop).select_related('brand').order_by('name')
    brands = Brand.objects.filter(business=workshop)

    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        brand_id = request.POST.get('brand')
        contact_person = request.POST.get('contact_person', '').strip()
        phone = request.POST.get('phone', '').strip()
        address = request.POST.get('address', '').strip()
        notes = request.POST.get('notes', '').strip()

        if name:
            brand_obj = Brand.objects.filter(id=brand_id).first() if brand_id else None
            Dealer.objects.create(
                business=workshop,
                name=name,
                brand=brand_obj,
                contact_person=contact_person,
                phone=phone,
                address=address or "Damak, Jhapa",
                notes=notes
            )
            messages.success(request, f"Dealer '{name}' registered successfully.")
            return redirect('billing:dealer_list')

    context = {
        'dealers': dealers,
        'brands': brands,
    }
    return render(request, 'billing/dealer_list.html', context)
