from django.contrib import admin
from .models import TeamMember, HealthData, ClinicSettings


@admin.register(TeamMember)
class TeamMemberAdmin(admin.ModelAdmin):
    list_display = ("full_name", "position")
    search_fields = ("full_name",)


@admin.register(HealthData)
class HealthDataAdmin(admin.ModelAdmin):
    list_display = ("member", "temperature", "risk_level", "risk_score", "created_at")
    list_filter = ("risk_level", "created_at")
    search_fields = ("member__full_name",)
    readonly_fields = ("risk_score", "risk_level")


@admin.register(ClinicSettings)
class ClinicSettingsAdmin(admin.ModelAdmin):
    list_display = ("name", "phone")