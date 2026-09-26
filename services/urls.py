from django.urls import path
from . import views

app_name = 'services'

urlpatterns = [
    path('', views.job_list_view, name='job_list'),
    path('new/', views.job_create_view, name='job_create'),
    path('tech-hub/', views.job_technician_view, name='technician_view'),
    path('<int:pk>/', views.job_detail_view, name='job_detail'),
    path('<int:pk>/status/', views.job_update_status_view, name='job_update_status'),
    path('<int:pk>/work-log/', views.job_add_work_log_view, name='job_add_work_log'),
    path('<int:pk>/parts/add/', views.job_add_part_view, name='job_add_part'),
    path('<int:pk>/parts/<int:part_id>/remove/', views.job_remove_part_view, name='job_remove_part'),
    path('<int:pk>/financials/', views.job_update_financials_view, name='job_update_financials'),
    path('<int:pk>/payment/', views.job_record_payment_view, name='job_record_payment'),
]
