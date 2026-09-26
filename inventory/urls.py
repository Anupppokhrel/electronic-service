from django.urls import path
from . import views

app_name = 'inventory'

urlpatterns = [
    path('', views.inventory_list_view, name='inventory_list'),
    path('new/', views.inventory_create_view, name='inventory_create'),
    path('<int:pk>/', views.inventory_item_detail_view, name='inventory_detail'),
    path('<int:pk>/edit/', views.inventory_edit_view, name='inventory_edit'),
    path('<int:pk>/adjust/', views.inventory_adjust_stock_view, name='inventory_adjust'),
    path('brands/', views.brand_list_view, name='brand_list'),
    path('brands/new/', views.brand_create_view, name='brand_create'),
    path('brands/<int:pk>/', views.brand_detail_view, name='brand_detail'),
]
