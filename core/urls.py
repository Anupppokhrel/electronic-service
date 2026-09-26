from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    path('', views.dashboard_view, name='dashboard'),
    path('search/', views.global_search_view, name='search'),
    path('settings/', views.settings_view, name='settings'),
    path('settings/payment-qr/', views.payment_qr_settings_view, name='payment_qr_settings'),
    path('activity-logs/', views.activity_logs_view, name='activity_logs'),
]
