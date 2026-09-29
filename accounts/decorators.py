from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages

def admin_required(view_func):
    """
    Restricts access to Owner / Admin only.
    Technicians attempting to access restricted management areas
    are redirected to their Field Work Hub.
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('accounts:login')
        profile = getattr(request.user, 'staff_profile', None)
        if profile and profile.is_technician:
            messages.warning(request, "Access restricted to workshop owner/admin. You have been redirected to your Field Work Hub.")
            return redirect('services:technician_view')
        return view_func(request, *args, **kwargs)
    return _wrapped_view

