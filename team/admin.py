from django.contrib import admin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from django.db.models import Count, Avg
from unfold.admin import ModelAdmin
from unfold.decorators import display
from .models import TeamMember, HealthData, ClinicSettings


# Sidebar uchun badge count
def get_member_count(request):
    return TeamMember.objects.count()


@admin.register(TeamMember)
class TeamMemberAdmin(ModelAdmin):
    list_display = ("full_name", "position", "age", "health_status")
    search_fields = ("full_name", "position")
    list_per_page = 20
    list_filter_submit = True

    fieldsets = (
        ("👤 Shaxsiy ma'lumotlar", {
            "fields": ("full_name", "age", "position"),
        }),
    )

    @display(description="Sog'liq holati", ordering="healthdata__risk_level")
    def health_status(self, obj):
        last = obj.healthdata_set.order_by('-created_at').first()
        if not last:
            return format_html(
                '<span style="color:#6b7280;font-size:12px;">— Ma\'lumot yo\'q</span>'
            )
        colors = {"past": "#22c55e", "orta": "#f59e0b", "yuqori": "#ef4444"}
        icons  = {"past": "✅", "orta": "⚠️", "yuqori": "🚨"}
        labels = {"past": "Sog'lom", "orta": "Kuzatuv", "yuqori": "Xavfli"}
        c = colors.get(last.risk_level, "#6b7280")
        i = icons.get(last.risk_level, "•")
        l = labels.get(last.risk_level, last.risk_level)
        return format_html(
            '<span style="background:{};color:white;padding:3px 12px;border-radius:20px;font-size:12px;font-weight:600;">{} {}</span>',
            c, i, l
        )


@admin.register(HealthData)
class HealthDataAdmin(ModelAdmin):
    list_display = ("member", "temperature_display", "risk_badge", "risk_score", "symptoms", "created_at")
    list_filter = ("risk_level", "symptoms", "close_contact", "chronic_disease")
    search_fields = ("member__full_name",)
    readonly_fields = ("risk_score", "risk_level", "recommendation")
    list_per_page = 20
    date_hierarchy = "created_at"
    list_filter_submit = True

    fieldsets = (
        ("👤 Xodim", {
            "fields": ("member",),
        }),
        ("🌡️ Sog'liq ko'rsatkichlari", {
            "fields": ("temperature", "symptoms", "close_contact", "chronic_disease"),
        }),
        ("📊 Natija (avtomatik hisoblanadi)", {
            "fields": ("risk_score", "risk_level", "recommendation"),
            "classes": ("collapse",),
        }),
    )

    @display(description="Harorat", ordering="temperature")
    def temperature_display(self, obj):
        color = "#ef4444" if obj.temperature > 37.5 else "#22c55e"
        return format_html(
            '<span style="color:{};font-weight:600;">{}°C</span>',
            color, obj.temperature
        )

    @display(description="Xavf darajasi", ordering="risk_level")
    def risk_badge(self, obj):
        colors = {"past": "#22c55e", "orta": "#f59e0b", "yuqori": "#ef4444"}
        labels = {"past": "✅ Past", "orta": "⚠️ O'rta", "yuqori": "🚨 Yuqori"}
        color = colors.get(obj.risk_level, "#6b7280")
        label = labels.get(obj.risk_level, obj.risk_level or "—")
        return format_html(
            '<span style="background:{};color:white;padding:3px 12px;border-radius:20px;font-size:12px;font-weight:600;">{}</span>',
            color, label
        )


@admin.register(ClinicSettings)
class ClinicSettingsAdmin(ModelAdmin):
    list_display = ("name", "phone", "address")

    fieldsets = (
        ("🏥 Klinika ma'lumotlari", {
            "fields": ("name", "phone", "address"),
        }),
    )