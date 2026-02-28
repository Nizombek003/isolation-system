from django.contrib import admin
from django.contrib.auth.models import Group
from .models import TeamMember, HealthData, ClinicSettings


# ==========================================
# TEAM MEMBER ADMIN
# ==========================================

@admin.register(TeamMember)
class TeamMemberAdmin(admin.ModelAdmin):
    list_display = ("full_name", "position")
    search_fields = ("full_name",)

    def has_module_permission(self, request):
        # Doctor ko‘rmasin
        if request.user.groups.filter(name='Doctor').exists():
            return False
        return request.user.is_superuser or request.user.groups.filter(name='Admin').exists()


# ==========================================
# HEALTH DATA ADMIN
# ==========================================

@admin.register(HealthData)
class HealthDataAdmin(admin.ModelAdmin):
    list_display = ("member", "temperature", "risk_level", "risk_score", "created_at")
    list_filter = ("risk_level", "created_at")
    search_fields = ("member__full_name",)
    readonly_fields = ("risk_score", "risk_level")

    def has_module_permission(self, request):
        # Doctor va Admin ko‘rsin
        if request.user.groups.filter(name='Doctor').exists():
            return True
        return request.user.is_superuser or request.user.groups.filter(name='Admin').exists()


# ==========================================
# CLINIC SETTINGS (FAKAT 1 TA BO‘LADI)
# ==========================================

@admin.register(ClinicSettings)
class ClinicSettingsAdmin(admin.ModelAdmin):
    list_display = ("name", "phone")
    search_fields = ("name",)

    def has_add_permission(self, request):
        # Faqat 1 ta ClinicSettings bo‘lishi mumkin
        if ClinicSettings.objects.exists():
            return False
        return request.user.is_superuser or request.user.groups.filter(name='Admin').exists()

    def has_module_permission(self, request):
        # Doctor ko‘rmasin
        if request.user.groups.filter(name='Doctor').exists():
            return False
        return request.user.is_superuser or request.user.groups.filter(name='Admin').exists()


# ==========================================
# GROUP ADMIN (faqat superuser)
# ==========================================

class GroupAdmin(admin.ModelAdmin):
    def has_module_permission(self, request):
        return request.user.is_superuser


admin.site.unregister(Group)
admin.site.register(Group, GroupAdmin)