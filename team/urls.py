from django.contrib.auth.views import LogoutView
from django.urls import path
from django.views.generic.base import RedirectView

from .views import (
    CustomLoginView,
    add_health,
    dashboard,
    generate_report,
    monthly_trend,
    patient_detail,
)

urlpatterns = [
    path("", RedirectView.as_view(pattern_name="dashboard", permanent=False), name="index"),
    path("login/", CustomLoginView.as_view(), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("dashboard/", dashboard, name="dashboard"),
    path("patients/<int:member_id>/", patient_detail, name="patient_detail"),
    path("report/", generate_report, name="report"),
    path("add-health/", add_health, name="add_health"),
    path("monthly-trend/", monthly_trend, name="monthly_trend"),
    
]
