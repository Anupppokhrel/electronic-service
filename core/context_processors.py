from core.models import Business
from inventory.models import InventoryItem
from services.models import ServiceJob

def workshop_context(request):
    workshop = Business.objects.first()
    context = {
        'workshop': workshop,
        'low_stock_count': 0,
        'active_jobs_count': 0,
        'staff_profile': None,
    }

    if workshop:
        # Check low stock
        context['low_stock_count'] = InventoryItem.objects.filter(
            business=workshop,
            quantity__lte=models_f_expression()
        ).count() if hasattr(InventoryItem, 'objects') else 0

    if request.user.is_authenticated:
        if hasattr(request.user, 'staff_profile'):
            context['staff_profile'] = request.user.staff_profile
        if workshop:
            context['active_jobs_count'] = ServiceJob.objects.filter(
                business=workshop,
                status='IN_PROGRESS'
            ).count()

    return context

def models_f_expression():
    from django.db.models import F
    return F('minimum_stock')
