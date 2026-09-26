from django.urls import path
from . import views

app_name = 'customers'

urlpatterns = [
    path('', views.customer_list_view, name='customer_list'),
    path('new/', views.customer_create_view, name='customer_create'),
    path('<int:pk>/', views.customer_detail_view, name='customer_detail'),
    path('<int:pk>/edit/', views.customer_edit_view, name='customer_edit'),
    path('<int:pk>/add-appliance/', views.customer_add_appliance_view, name='customer_add_appliance'),
    path('lookup/', views.customer_lookup_api, name='customer_lookup'),
]
