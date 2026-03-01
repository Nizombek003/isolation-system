from django.urls import path
from django.contrib.auth.views import LogoutView
from .views import dashboard, generate_report, add_health, monthly_trend, CustomLoginView
from .views import create_admin
urlpatterns = [
    path('login/', CustomLoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('dashboard/', dashboard, name='dashboard'),
    path('report/', generate_report, name='report'),
    path('add-health/', add_health, name='add_health'),
    path('monthly-trend/', monthly_trend, name='monthly_trend'),
    path('create-admin/', create_admin),
]