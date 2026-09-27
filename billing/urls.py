from django.urls import path
from . import views

app_name = 'billing'

urlpatterns = [
    path('', views.invoice_list_view, name='invoice_list'),
    path('due/', views.credit_ledger_view, name='credit_ledger'),
    path('warranty-claims/', views.warranty_claims_view, name='warranty_claims'),
    path('warranty-claims/export/', views.warranty_claims_export_excel, name='warranty_claims_export_excel'),
    path('warranty-claims/<int:pk>/status/', views.warranty_claim_update_status, name='warranty_claim_update_status'),
    path('dealers/', views.dealers_list_view, name='dealer_list'),
    path('<int:pk>/', views.invoice_detail_view, name='invoice_detail'),
    path('<int:pk>/pay/', views.invoice_record_payment_view, name='invoice_record_payment'),
]
