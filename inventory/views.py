from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, F, Sum, Count
from decimal import Decimal
from accounts.decorators import admin_required
from core.models import Business, ActivityLog
from .models import InventoryItem, Brand, Category, StockTransaction

@login_required
def inventory_list_view(request):
    workshop = Business.objects.first()
    search = request.GET.get('search', '').strip()
    category_id = request.GET.get('category')
    brand_id = request.GET.get('brand')
    inv_type = request.GET.get('type')
    low_stock = request.GET.get('low_stock')

    items = InventoryItem.objects.filter(business=workshop).select_related('brand', 'category')

    if search:
        items = items.filter(
            Q(part_name__icontains=search) |
            Q(part_code__icontains=search) |
            Q(supplier__icontains=search)
        )
    if category_id:
        items = items.filter(category_id=category_id)
    if brand_id:
        items = items.filter(brand_id=brand_id)
    if inv_type:
        items = items.filter(inventory_type=inv_type)
    if low_stock == '1':
        items = items.filter(quantity__lte=F('minimum_stock'))

    categories = Category.objects.filter(business=workshop)
    brands = Brand.objects.filter(business=workshop)

    # Low stock counter
    total_low_stock = InventoryItem.objects.filter(
        business=workshop,
        quantity__lte=F('minimum_stock')
    ).count()

    context = {
        'items': items,
        'categories': categories,
        'brands': brands,
        'search': search,
        'selected_category': category_id,
        'selected_brand': brand_id,
        'selected_type': inv_type,
        'low_stock_filter': low_stock,
        'total_low_stock': total_low_stock,
    }
    return render(request, 'inventory/inventory_list.html', context)

@login_required
def inventory_item_detail_view(request, pk):
    item = get_object_or_404(InventoryItem, pk=pk)
    transactions = item.transactions.select_related('performed_by').order_by('-created_at')[:25]
    job_usages = item.job_usages.select_related('job', 'added_by').order_by('-added_at')[:25]

    context = {
        'item': item,
        'transactions': transactions,
        'job_usages': job_usages,
    }
    return render(request, 'inventory/inventory_detail.html', context)

@admin_required
def inventory_create_view(request):
    workshop = Business.objects.first()
    categories = Category.objects.filter(business=workshop)
    brands = Brand.objects.filter(business=workshop)

    if request.method == 'POST':
        part_name = request.POST.get('part_name', '').strip()
        part_code = request.POST.get('part_code', '').strip()
        category_id = request.POST.get('category')
        brand_id = request.POST.get('brand')
        inventory_type = request.POST.get('inventory_type', 'BRAND_SPECIFIC')
        quantity = Decimal(request.POST.get('quantity', '0') or '0')
        minimum_stock = Decimal(request.POST.get('minimum_stock', '2') or '2')
        unit = request.POST.get('unit', 'pcs')
        purchase_price = Decimal(request.POST.get('purchase_price', '0') or '0')
        selling_price = Decimal(request.POST.get('selling_price', '0') or '0')
        supplier = request.POST.get('supplier', '').strip()
        storage_bin = request.POST.get('storage_bin', '').strip()
        notes = request.POST.get('notes', '').strip()

        if not part_name:
            messages.error(request, "Part name is required.")
            return render(request, 'inventory/inventory_form.html', {'categories': categories, 'brands': brands, 'action': 'Add'})

        item = InventoryItem.objects.create(
            business=workshop,
            part_name=part_name,
            part_code=part_code,
            category_id=category_id if category_id else None,
            brand_id=brand_id if brand_id else None,
            inventory_type=inventory_type,
            quantity=quantity,
            minimum_stock=minimum_stock,
            unit=unit,
            purchase_price=purchase_price,
            selling_price=selling_price,
            supplier=supplier,
            storage_bin=storage_bin,
            notes=notes
        )

        # Initial stock transaction if initial quantity > 0
        if quantity > 0:
            StockTransaction.objects.create(
                item=item,
                transaction_type='PURCHASE',
                quantity_change=quantity,
                balance_after=quantity,
                unit_price=purchase_price,
                performed_by=request.user,
                notes="Initial inventory opening stock"
            )

        ActivityLog.objects.create(
            business=workshop,
            user=request.user,
            action=f"Added inventory item: {item.part_name}",
            action_type="STOCK_UPDATE",
            details=f"Added {item.part_name} with stock {item.quantity} {item.unit}"
        )
        messages.success(request, f"Item {item.part_name} added to inventory.")
        return redirect('inventory:inventory_detail', pk=item.pk)

    return render(request, 'inventory/inventory_form.html', {'categories': categories, 'brands': brands, 'action': 'Add'})

@admin_required
def inventory_edit_view(request, pk):
    item = get_object_or_404(InventoryItem, pk=pk)
    categories = Category.objects.filter(business=item.business)
    brands = Brand.objects.filter(business=item.business)

    if request.method == 'POST':
        item.part_name = request.POST.get('part_name', item.part_name).strip()
        item.part_code = request.POST.get('part_code', item.part_code).strip()
        item.category_id = request.POST.get('category') or None
        item.brand_id = request.POST.get('brand') or None
        item.inventory_type = request.POST.get('inventory_type', item.inventory_type)
        item.minimum_stock = Decimal(request.POST.get('minimum_stock', item.minimum_stock) or '0')
        item.unit = request.POST.get('unit', item.unit)
        item.purchase_price = Decimal(request.POST.get('purchase_price', item.purchase_price) or '0')
        item.selling_price = Decimal(request.POST.get('selling_price', item.selling_price) or '0')
        item.supplier = request.POST.get('supplier', item.supplier).strip()
        item.storage_bin = request.POST.get('storage_bin', item.storage_bin).strip()
        item.notes = request.POST.get('notes', item.notes).strip()
        item.save()

        messages.success(request, f"Inventory item {item.part_name} updated.")
        return redirect('inventory:inventory_detail', pk=item.pk)

    return render(request, 'inventory/inventory_form.html', {'item': item, 'categories': categories, 'brands': brands, 'action': 'Edit'})

@admin_required
def inventory_adjust_stock_view(request, pk):
    item = get_object_or_404(InventoryItem, pk=pk)
    if request.method == 'POST':
        action_type = request.POST.get('action_type') # PURCHASE or ADJUSTMENT
        qty = Decimal(request.POST.get('quantity', '0') or '0')
        unit_price = Decimal(request.POST.get('unit_price', '0') or str(item.purchase_price))
        notes = request.POST.get('notes', '').strip()

        if qty <= 0:
            messages.error(request, "Quantity must be greater than zero.")
            return redirect('inventory:inventory_detail', pk=pk)

        if action_type == 'PURCHASE':
            item.quantity += qty
            StockTransaction.objects.create(
                item=item,
                transaction_type='PURCHASE',
                quantity_change=qty,
                balance_after=item.quantity,
                unit_price=unit_price,
                performed_by=request.user,
                notes=notes or "Restocked inventory"
            )
            item.save()
            ActivityLog.objects.create(
                business=item.business,
                user=request.user,
                action=f"Restocked {item.part_name} (+{qty} {item.unit})",
                action_type="STOCK_UPDATE"
            )
            messages.success(request, f"Added {qty} {item.unit} to {item.part_name}.")

        elif action_type == 'ADJUSTMENT':
            # Could be decrease or increase
            direction = request.POST.get('direction', 'ADD') # ADD or SUBTRACT
            change = qty if direction == 'ADD' else -qty
            if item.quantity + change < 0:
                messages.error(request, "Cannot adjust stock below zero.")
                return redirect('inventory:inventory_detail', pk=pk)

            item.quantity += change
            StockTransaction.objects.create(
                item=item,
                transaction_type='ADJUSTMENT',
                quantity_change=change,
                balance_after=item.quantity,
                unit_price=unit_price,
                performed_by=request.user,
                notes=notes or f"Manual adjustment: {direction}"
            )
            item.save()
            ActivityLog.objects.create(
                business=item.business,
                user=request.user,
                action=f"Stock adjusted for {item.part_name} ({change:+f} {item.unit})",
                action_type="STOCK_UPDATE"
            )
            messages.success(request, f"Adjusted stock for {item.part_name}.")

    return redirect('inventory:inventory_detail', pk=pk)

# Brands
@admin_required
def brand_list_view(request):
    workshop = Business.objects.first()
    brands = Brand.objects.filter(business=workshop).annotate(
        items_count=Count('inventory_items')
    ).order_by('name')

    context = {'brands': brands}
    return render(request, 'inventory/brand_list.html', context)

@admin_required
def brand_detail_view(request, pk):
    brand = get_object_or_404(Brand, pk=pk)
    inventory_items = brand.inventory_items.all().order_by('part_name')

    # Service jobs for this brand (either by ACUnit.brand or ac_brand_name)
    from services.models import ServiceJob
    jobs = ServiceJob.objects.filter(
        business=brand.business
    ).filter(
        Q(ac_unit__brand=brand) | Q(ac_brand_name__iexact=brand.name)
    ).select_related('customer', 'technician').order_by('-created_at')

    # Parts consumed for this brand
    from services.models import JobPart
    parts_consumed = JobPart.objects.filter(
        inventory_item__brand=brand
    ).select_related('inventory_item', 'job').order_by('-added_at')[:20]

    context = {
        'brand': brand,
        'inventory_items': inventory_items,
        'jobs': jobs[:20],
        'total_jobs_count': jobs.count(),
        'parts_consumed': parts_consumed,
    }
    return render(request, 'inventory/brand_detail.html', context)

@admin_required
def brand_create_view(request):
    workshop = Business.objects.first()
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        code = request.POST.get('code', '').strip()
        is_common = 'is_common' in request.POST
        description = request.POST.get('description', '').strip()
        website = request.POST.get('website', '').strip()

        if not name:
            messages.error(request, "Brand name is required.")
            return render(request, 'inventory/brand_form.html', {'action': 'Add'})

        brand = Brand.objects.create(
            business=workshop,
            name=name,
            code=code,
            is_common=is_common,
            description=description,
            website=website
        )
        ActivityLog.objects.create(
            business=workshop,
            user=request.user,
            action=f"Added new brand: {brand.name}",
            action_type="SYSTEM"
        )
        messages.success(request, f"Brand {brand.name} created successfully.")
        return redirect('inventory:brand_detail', pk=brand.pk)

    return render(request, 'inventory/brand_form.html', {'action': 'Add'})
