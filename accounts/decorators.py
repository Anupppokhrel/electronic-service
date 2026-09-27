from functools import wraps
from django.shortcuts import redirect

def admin_required(view_func):
    """
    Unified Workshop Access:
    All authenticated workshop staff & owner have full seamless access to workshop operations.
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('accounts:login')
        return view_func(request, *args, **kwargs)
    return _wrapped_view

