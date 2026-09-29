from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.models import User
from django.db.models import Count, Sum
from core.models import Business, ActivityLog
from .models import StaffProfile
from .decorators import admin_required

def login_view(request):
    if request.user.is_authenticated:
        return redirect('core:dashboard')

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '').strip()
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            messages.success(request, f"Welcome back, {user.get_full_name() or user.username}!")
            next_url = request.GET.get('next')
            if not next_url or next_url == '/':
                if hasattr(user, 'staff_profile') and user.staff_profile.is_technician:
                    return redirect('services:technician_view')
                return redirect('core:dashboard')
            return redirect(next_url)
        else:
            messages.error(request, "Invalid username or password. Please try again.")

    workshop = Business.objects.first()
    return render(request, 'accounts/login.html', {'workshop': workshop})

def logout_view(request):
    logout(request)
    messages.info(request, "You have been logged out.")
    return redirect('accounts:login')

@admin_required
def staff_list_view(request):
    workshop = Business.objects.first()
    staff_profiles = StaffProfile.objects.filter(
        business=workshop
    ).select_related('user').order_by('role', 'user__first_name')

    context = {
        'staff_profiles': staff_profiles,
        'total_staff': staff_profiles.count(),
        'available_count': staff_profiles.filter(status='AVAILABLE').count(),
        'working_count': staff_profiles.filter(status='WORKING').count(),
    }
    return render(request, 'accounts/staff_list.html', context)

@admin_required
def staff_detail_view(request, pk):
    profile = get_object_or_404(StaffProfile, pk=pk)
    user = profile.user

    assigned_jobs = user.assigned_jobs.select_related('customer').order_by('-created_at')
    active_job = assigned_jobs.filter(status='IN_PROGRESS').first()
    completed_jobs = assigned_jobs.filter(status__in=['COMPLETED', 'CLOSED'])

    # Recent work logs performed by this staff
    recent_work = user.worklog_set.select_related('job').order_by('-created_at')[:10] if hasattr(user, 'worklog_set') else []
    
    # Parts added by this staff
    parts_used = user.jobpart_set.select_related('inventory_item', 'job').order_by('-added_at')[:15] if hasattr(user, 'jobpart_set') else []

    context = {
        'profile': profile,
        'active_job': active_job,
        'assigned_jobs': assigned_jobs[:20],
        'total_assigned': assigned_jobs.count(),
        'total_completed': completed_jobs.count(),
        'recent_work': recent_work,
        'parts_used': parts_used,
    }
    return render(request, 'accounts/staff_detail.html', context)

@login_required
def staff_status_update_view(request, pk):
    profile = get_object_or_404(StaffProfile, pk=pk)
    if not (request.user.staff_profile.is_admin or request.user == profile.user):
        messages.error(request, "Permission denied.")
        return redirect('accounts:staff_detail', pk=pk)

    if request.method == 'POST':
        new_status = request.POST.get('status')
        if new_status in dict(StaffProfile.STATUS_CHOICES):
            profile.status = new_status
            profile.save()
            ActivityLog.objects.create(
                business=profile.business,
                user=request.user,
                action=f"Updated status of {profile.user.get_full_name()} to {profile.get_status_display()}",
                action_type="STAFF"
            )
            messages.success(request, f"Status updated to {profile.get_status_display()}.")

    return redirect('accounts:staff_detail', pk=pk)
