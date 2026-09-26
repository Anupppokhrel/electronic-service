from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from decimal import Decimal
from accounts.decorators import admin_required
from core.models import Business, ActivityLog
from .models import Customer

@admin_required
def customer_list_view(request):
    workshop = Business.objects.first()
    search = request.GET.get('search', '').strip()

    customers = Customer.objects.filter(business=workshop)
    if search:
        customers = customers.filter(
            Q(name__icontains=search) |
            Q(phone__icontains=search) |
            Q(address__icontains=search)
        )

    customers = customers.order_by('-updated_at')

    context = {
        'customers': customers,
        'search': search,
        'total_customers': customers.count(),
    }
    return render(request, 'customers/customer_list.html', context)

@admin_required
def customer_detail_view(request, pk):
    customer = get_object_or_404(Customer, pk=pk)
    service_jobs = customer.service_jobs.select_related('technician', 'ac_unit').order_by('-created_at')
    ac_units = customer.ac_units.select_related('brand').order_by('-created_at')
    workshop = customer.business
    from inventory.models import Brand
    from services.models import ACUnit
    brands = Brand.objects.filter(business=workshop)

    context = {
        'customer': customer,
        'service_jobs': service_jobs,
        'ac_units': ac_units,
        'total_jobs': customer.total_jobs,
        'last_service': customer.last_service,
        'total_spent': customer.total_spent,
        'brands': brands,
        'appliance_choices': ACUnit.APPLIANCE_CHOICES,
    }
    return render(request, 'customers/customer_detail.html', context)

@admin_required
def customer_create_view(request):
    workshop = Business.objects.first()
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        phone = request.POST.get('phone', '').strip()
        address = request.POST.get('address', '').strip()
        landmark = request.POST.get('landmark', '').strip()
        alt_phone = request.POST.get('alt_phone', '').strip()
        notes = request.POST.get('notes', '').strip()

        if not name or not phone:
            messages.error(request, "Customer name and phone number are required.")
            return render(request, 'customers/customer_form.html', {'action': 'Create'})

        # Check existing
        existing = Customer.objects.filter(business=workshop, phone=phone).first()
        if existing:
            messages.warning(request, f"Customer with phone {phone} already exists ({existing.name}).")
            return redirect('customers:customer_detail', pk=existing.pk)

        default_addr = workshop.address if workshop else ""
        customer = Customer.objects.create(
            business=workshop,
            name=name,
            phone=phone,
            address=address or default_addr,
            landmark=landmark,
            alt_phone=alt_phone,
            notes=notes
        )

        ActivityLog.objects.create(
            business=workshop,
            user=request.user,
            action=f"Created customer profile for {customer.name}",
            action_type="SYSTEM"
        )
        messages.success(request, f"Customer {customer.name} created successfully.")
        return redirect('customers:customer_detail', pk=customer.pk)

    return render(request, 'customers/customer_form.html', {'action': 'Create'})

@admin_required
def customer_edit_view(request, pk):
    customer = get_object_or_404(Customer, pk=pk)
    if request.method == 'POST':
        customer.name = request.POST.get('name', customer.name).strip()
        customer.address = request.POST.get('address', customer.address).strip()
        customer.landmark = request.POST.get('landmark', customer.landmark).strip()
        customer.alt_phone = request.POST.get('alt_phone', customer.alt_phone).strip()
        customer.notes = request.POST.get('notes', customer.notes).strip()
        customer.save()

        messages.success(request, f"Customer {customer.name} updated successfully.")
        return redirect('customers:customer_detail', pk=customer.pk)

    return render(request, 'customers/customer_form.html', {'action': 'Edit', 'customer': customer})

@admin_required
def customer_lookup_api(request):
    """AJAX endpoint for instant customer lookup by phone number during job creation"""
    phone = request.GET.get('phone', '').strip()
    customer_id = request.GET.get('customer_id', '').strip()
    workshop = Business.objects.first()

    customer = None
    if customer_id:
        customer = Customer.objects.filter(business=workshop, id=customer_id).first()
    elif phone and len(phone) >= 4:
        customer = Customer.objects.filter(business=workshop, phone=phone).first()

    if customer:
        units = [
            {
                'id': u.id,
                'appliance_type': u.appliance_type,
                'appliance_name': u.get_appliance_type_display(),
                'brand': u.brand.name if u.brand else '',
                'brand_id': u.brand.id if u.brand else '',
                'ac_type': u.ac_type,
                'capacity': u.capacity,
                'model_number': u.model_number,
                'location_notes': u.location_notes
            }
            for u in customer.ac_units.select_related('brand')
        ]
        return JsonResponse({
            'found': True,
            'id': customer.id,
            'name': customer.name,
            'phone': customer.phone,
            'address': customer.address,
            'landmark': customer.landmark,
            'total_jobs': customer.total_jobs,
            'units': units
        })
    return JsonResponse({'found': False})

@admin_required
def customer_add_appliance_view(request, pk):
    customer = get_object_or_404(Customer, pk=pk)
    if request.method == 'POST':
        appliance_type = request.POST.get('appliance_type', 'AC')
        brand_id = request.POST.get('brand')
        from inventory.models import Brand
        from services.models import ACUnit
        brand_obj = Brand.objects.filter(id=brand_id).first() if brand_id else None
        ac_type = request.POST.get('ac_type', 'Split AC')
        capacity = request.POST.get('capacity', '1.5 Ton')
        model_number = request.POST.get('model_number', '').strip()
        serial_number = request.POST.get('serial_number', '').strip()
        location_notes = request.POST.get('location_notes', '').strip()

        unit = ACUnit.objects.create(
            customer=customer,
            appliance_type=appliance_type,
            brand=brand_obj,
            ac_type=ac_type,
            capacity=capacity,
            model_number=model_number,
            serial_number=serial_number,
            location_notes=location_notes
        )
        ActivityLog.objects.create(
            business=customer.business,
            user=request.user,
            action=f"Registered {unit.get_appliance_type_display()} for customer {customer.name}",
            action_type="SYSTEM"
        )
        messages.success(request, f"{unit.get_appliance_type_display()} registered for {customer.name}.")
    return redirect('customers:customer_detail', pk=customer.pk)
