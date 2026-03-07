from django.contrib import admin
from django.utils.html import format_html
from unfold.admin import ModelAdmin
from .models import TeamMember, HealthData, ClinicSettings


@admin.register(TeamMember)
class TeamMemberAdmin(ModelAdmin):
    list_display = ("full_name", "position", "age")
    search_fields = ("full_name", "position")
    list_per_page = 20

    fieldsets = (
        ("Shaxsiy ma'lumotlar", {
            "fields": ("full_name", "age", "position"),
        }),
    )


@admin.register(HealthData)
class HealthDataAdmin(ModelAdmin):
    list_display = ("member", "temperature", "risk_badge", "risk_score", "created_at")
    list_filter = ("risk_level", "created_at")
    search_fields = ("member__full_name",)
    readonly_fields = ("risk_score", "risk_level", "recommendation")
    list_per_page = 20

    fieldsets = (
        ("Xodim", {
            "fields": ("member",),
        }),
        ("Sog'liq ko'rsatkichlari", {
            "fields": ("temperature", "symptoms", "close_contact", "chronic_disease"),
        }),
        ("Natija (avtomatik)", {
            "fields": ("risk_score", "risk_level", "recommendation"),
            "classes": ("collapse",),
        }),
    )

    def risk_badge(self, obj):
        colors = {
            "past": "#22c55e",
            "orta": "#f59e0b",
            "yuqori": "#ef4444",
        }
        labels = {
            "past": "🟢 Past",
            "orta": "🟡 O'rta",
            "yuqori": "🔴 Yuqori",
        }
        color = colors.get(obj.risk_level, "#6b7280")
        label = labels.get(obj.risk_level, obj.risk_level)
        return format_html(
            '<span style="background:{}; color:white; padding:3px 10px; border-radius:12px; font-weight:600; font-size:12px;">{}</span>',
            color, label
        )
    risk_badge.short_description = "Xavf darajasi"


@admin.register(ClinicSettings)
class ClinicSettingsAdmin(ModelAdmin):
    list_display = ("name", "phone", "address")

    fieldsets = (
        ("Klinika ma'lumotlari", {
            "fields": ("name", "phone", "address"),
        }),
    )