from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages

def admin_required(view_func):
    """
    Decorator to restrict view access strictly to Workshop Owners / Admins.
    Technicians attempting access are safely redirected to their Technician Work Hub.
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('accounts:login')
        
        is_admin = request.user.is_superuser
        if hasattr(request.user, 'staff_profile'):
            if request.user.staff_profile.is_admin:
                is_admin = True
        
        if not is_admin:
            messages.error(request, "Access restricted: Only the workshop owner/admin can access this section.")
            if hasattr(request.user, 'staff_profile') and request.user.staff_profile.is_technician:
                return redirect('services:technician_view')
            return redirect('accounts:login')
        
        return view_func(request, *args, **kwargs)
    return _wrapped_view
