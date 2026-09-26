from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('staff/', views.staff_list_view, name='staff_list'),
    path('staff/<int:pk>/', views.staff_detail_view, name='staff_detail'),
    path('staff/<int:pk>/status/', views.staff_status_update_view, name='staff_status_update'),
]
