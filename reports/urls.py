from django.urls import path
from . import views

app_name = 'reports'

urlpatterns = [
    path('', views.reports_index_view, name='reports_index'),
    path('export/csv/', views.export_jobs_csv, name='export_csv'),
    path('export/excel/', views.export_jobs_excel, name='export_excel'),
    path('export/inventory/excel/', views.export_inventory_excel, name='export_inventory_excel'),
]
