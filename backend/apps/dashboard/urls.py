from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    path('', views.DashboardRedirectView.as_view(), name='redirect'),
    path('staff/', views.StaffDashboardView.as_view(), name='staff'),
    path('manager/', views.ManagerDashboardView.as_view(), name='manager'),
    path('admin/', views.AdminDashboardView.as_view(), name='admin'),
]