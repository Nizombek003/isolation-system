import json

from django.contrib import admin
from django import forms
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.contrib.auth.models import Group, User
from django.core.exceptions import PermissionDenied
from django.db.models import Count, Q
from django.utils.html import format_html
from unfold.admin import ModelAdmin
from unfold.decorators import display

from .hospital_catalog import get_hospital_autofill_map, get_hospital_choice_pairs
from .models import (
    ClinicSettings,
    DiseaseType,
    DoctorProfile,
    DoctorSpecialty,
    HealthData,
    IsolationCenter,
    Region,
    TeamMember,
)


ROLE_GROUPS = ("Admin", "Doctor", "Viewer")


def is_admin_user(user):
    return user.is_superuser or user.groups.filter(name="Admin").exists()


def is_doctor_user(user):
    return user.groups.filter(name="Doctor").exists()


def get_member_count(request):
    return TeamMember.objects.count()


def _doctor_user_queryset():
    return User.objects.filter(Q(is_superuser=True) | Q(groups__name="Doctor")).distinct()


def _set_user_role(queryset, role_name):
    role_group, _ = Group.objects.get_or_create(name=role_name)
    other_group_names = [name for name in ROLE_GROUPS if name != role_name]
    other_groups = list(Group.objects.filter(name__in=other_group_names))

    updated = 0
    for user in queryset:
        if other_groups:
            user.groups.remove(*other_groups)
        user.groups.add(role_group)
        if role_name == "Doctor":
            DoctorProfile.objects.get_or_create(user=user)
        updated += 1

    return updated


def _doctor_can_access_patient(user, patient):
    if patient is None:
        return True
    if is_admin_user(user):
        return True
    if is_doctor_user(user):
        return patient.assigned_doctor_id == user.id
    return True


@admin.register(DoctorSpecialty)
class DoctorSpecialtyAdmin(ModelAdmin):
    list_display = ("name", "doctor_count")
    search_fields = ("name",)

    @display(description="Shifokorlar soni")
    def doctor_count(self, obj):
        return obj.doctors.count()


@admin.register(DiseaseType)
class DiseaseTypeAdmin(ModelAdmin):
    list_display = ("name", "isolation_required", "patient_count")
    list_filter = ("isolation_required",)
    search_fields = ("name",)

    @display(description="Bemorlar soni")
    def patient_count(self, obj):
        return obj.patients.count()


@admin.register(DoctorProfile)
class DoctorProfileAdmin(ModelAdmin):
    list_display = ("user", "specialty", "room", "patient_count")
    search_fields = ("user__username", "user__first_name", "user__last_name", "specialty__name")
    list_filter = ("specialty",)

    @display(description="Bemorlar soni")
    def patient_count(self, obj):
        return obj.user.patients.count()


@admin.register(TeamMember)
class TeamMemberAdmin(ModelAdmin):
    list_display = (
        "full_name",
        "region",
        "disease_type",
        "assigned_doctor_display",
        "status",
        "age",
        "health_status",
    )
    search_fields = ("full_name", "position", "region__name", "disease_type__name", "assigned_doctor__username")
    list_filter = ("status", "region", "disease_type", "assigned_doctor")
    list_per_page = 20
    list_filter_submit = True

    fieldsets = (
        ("Bemor profili", {
            "fields": ("full_name", "age", "position", "region", "status"),
        }),
        ("Tibbiy bog'lanish", {
            "fields": ("disease_type", "assigned_doctor", "notes"),
        }),
    )

    def get_queryset(self, request):
        queryset = super().get_queryset(request).select_related("disease_type", "assigned_doctor")
        if is_doctor_user(request.user) and not is_admin_user(request.user):
            return queryset.filter(assigned_doctor=request.user)
        return queryset

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "assigned_doctor":
            kwargs["queryset"] = _doctor_user_queryset()
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def save_model(self, request, obj, form, change):
        if is_doctor_user(request.user) and not is_admin_user(request.user):
            obj.assigned_doctor = request.user
        super().save_model(request, obj, form, change)

    def has_view_permission(self, request, obj=None):
        return super().has_view_permission(request, obj) and _doctor_can_access_patient(request.user, obj)

    def has_change_permission(self, request, obj=None):
        return super().has_change_permission(request, obj) and _doctor_can_access_patient(request.user, obj)

    def has_delete_permission(self, request, obj=None):
        return super().has_delete_permission(request, obj) and _doctor_can_access_patient(request.user, obj)

    @display(description="Mas'ul shifokor", ordering="assigned_doctor__username")
    def assigned_doctor_display(self, obj):
        if not obj.assigned_doctor:
            return "-"

        specialty = getattr(getattr(obj.assigned_doctor, "doctor_profile", None), "specialty", None)
        if specialty:
            return f"{obj.assigned_doctor.get_username()} ({specialty.name})"
        return obj.assigned_doctor.get_username()

    @display(description="Sog'liq holati", ordering="healthdata__risk_level")
    def health_status(self, obj):
        last = obj.healthdata_set.order_by("-created_at").first()
        if not last:
            return format_html(
                '<span style="color:#6b7280;font-size:12px;">- Ma\'lumot yo\'q</span>'
            )

        colors = {"past": "#22c55e", "orta": "#f59e0b", "yuqori": "#ef4444"}
        labels = {"past": "Barqaror", "orta": "Kuzatuv", "yuqori": "Xavfli"}
        color = colors.get(last.risk_level, "#6b7280")
        label = labels.get(last.risk_level, last.risk_level)
        return format_html(
            '<span style="background:{};color:white;padding:3px 12px;border-radius:20px;font-size:12px;font-weight:600;">{}</span>',
            color,
            label,
        )


@admin.register(HealthData)
class HealthDataAdmin(ModelAdmin):
    list_display = (
        "member",
        "doctor_display",
        "disease_display",
        "temperature_display",
        "risk_badge",
        "entered_by",
        "created_at",
    )
    list_filter = (
        "risk_level",
        "symptoms",
        "close_contact",
        "chronic_disease",
        "member__disease_type",
        "member__assigned_doctor",
    )
    search_fields = ("member__full_name", "member__assigned_doctor__username", "entered_by__username")
    readonly_fields = ("risk_score", "risk_level", "recommendation", "entered_by")
    list_per_page = 20
    date_hierarchy = "created_at"
    list_filter_submit = True

    fieldsets = (
        ("Bemor", {
            "fields": ("member", "entered_by"),
        }),
        ("Sog'liq ko'rsatkichlari", {
            "fields": ("temperature", "symptoms", "close_contact", "chronic_disease"),
        }),
        ("Natija (avtomatik hisoblanadi)", {
            "fields": ("risk_score", "risk_level", "recommendation"),
            "classes": ("collapse",),
        }),
    )

    def get_queryset(self, request):
        queryset = super().get_queryset(request).select_related(
            "member",
            "member__assigned_doctor",
            "member__disease_type",
            "entered_by",
        )
        if is_doctor_user(request.user) and not is_admin_user(request.user):
            return queryset.filter(member__assigned_doctor=request.user)
        return queryset

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "member" and is_doctor_user(request.user) and not is_admin_user(request.user):
            kwargs["queryset"] = TeamMember.objects.filter(assigned_doctor=request.user)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def save_model(self, request, obj, form, change):
        if is_doctor_user(request.user) and not is_admin_user(request.user):
            if obj.member.assigned_doctor_id != request.user.id:
                raise PermissionDenied("Siz faqat o'zingizga biriktirilgan bemorlar uchun ma'lumot kirita olasiz.")
        obj.entered_by = request.user
        super().save_model(request, obj, form, change)

    def has_view_permission(self, request, obj=None):
        return super().has_view_permission(request, obj) and _doctor_can_access_patient(
            request.user,
            None if obj is None else obj.member,
        )

    def has_change_permission(self, request, obj=None):
        return super().has_change_permission(request, obj) and _doctor_can_access_patient(
            request.user,
            None if obj is None else obj.member,
        )

    def has_delete_permission(self, request, obj=None):
        return super().has_delete_permission(request, obj) and _doctor_can_access_patient(
            request.user,
            None if obj is None else obj.member,
        )

    @display(description="Harorat", ordering="temperature")
    def temperature_display(self, obj):
        color = "#ef4444" if obj.temperature > 37.5 else "#22c55e"
        return format_html(
            '<span style="color:{};font-weight:600;">{} C</span>',
            color,
            obj.temperature,
        )

    @display(description="Kasallik turi", ordering="member__disease_type__name")
    def disease_display(self, obj):
        return obj.member.disease_type.name if obj.member.disease_type else "-"

    @display(description="Shifokor", ordering="member__assigned_doctor__username")
    def doctor_display(self, obj):
        return obj.member.assigned_doctor.get_username() if obj.member.assigned_doctor else "-"

    @display(description="Xavf darajasi", ordering="risk_level")
    def risk_badge(self, obj):
        colors = {"past": "#22c55e", "orta": "#f59e0b", "yuqori": "#ef4444"}
        labels = {"past": "Past", "orta": "O'rta", "yuqori": "Yuqori"}
        color = colors.get(obj.risk_level, "#6b7280")
        label = labels.get(obj.risk_level, obj.risk_level or "-")
        return format_html(
            '<span style="background:{};color:white;padding:3px 12px;border-radius:20px;font-size:12px;font-weight:600;">{}</span>',
            color,
            label,
        )


@admin.register(IsolationCenter)
class IsolationCenterAdmin(ModelAdmin):
    class IsolationCenterAdminForm(forms.ModelForm):
        name = forms.ChoiceField(label="Markaz nomi", required=True, choices=())

        class Meta:
            model = IsolationCenter
            fields = "__all__"

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            choices = [("", "Kasalxonani tanlang")] + get_hospital_choice_pairs()
            self.fields["name"].choices = choices
            self.fields["name"].widget.attrs["data-hospital-map"] = json.dumps(
                get_hospital_autofill_map(),
                ensure_ascii=False,
            )

        def clean_name(self):
            selected = self.cleaned_data["name"]
            allowed_names = {name for name, _label in get_hospital_choice_pairs()}
            if selected not in allowed_names:
                raise forms.ValidationError("Faqat belgilangan 10 ta kasalxonadan tanlang.")
            return selected

    form = IsolationCenterAdminForm

    class Media:
        js = ("team/js/isolation_center_autofill.js",)

    list_display = (
        "name",
        "region",
        "capacity",
        "occupancy_rate",
        "readiness_score",
        "infrastructure_score",
        "travel_time_minutes",
        "is_active",
    )
    list_filter = ("is_active", "region")
    search_fields = ("name", "region__name", "address", "notes")

    @display(description="Manzil")
    def address_short(self, obj):
        if not obj.address:
            return "-"
        return obj.address[:50] + "..." if len(obj.address) > 50 else obj.address

    fieldsets = (
        ("Izolyatsiya markazi (jamoat salomatligi)", {
            "fields": (
                "name",
                "region",
                "address",
                "capacity",
                "occupancy_rate",
                "readiness_score",
                "infrastructure_score",
                "travel_time_minutes",
                "is_active",
                "notes",
            ),
        }),
    )


@admin.register(ClinicSettings)
class ClinicSettingsAdmin(ModelAdmin):
    list_display = ("name", "phone", "address")

    fieldsets = (
        ("Klinika ma'lumotlari", {
            "fields": ("name", "phone", "address"),
        }),
    )


try:
    admin.site.unregister(User)
except admin.sites.NotRegistered:
    pass


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    list_display = DjangoUserAdmin.list_display + ("role_display", "specialty_display", "patient_count")
    actions = ("set_role_admin", "set_role_doctor", "set_role_viewer")

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("doctor_profile__specialty").annotate(
            patient_total=Count("patients", distinct=True)
        )

    @admin.display(description="Role")
    def role_display(self, obj):
        if obj.is_superuser:
            return "Superuser"

        user_roles = obj.groups.filter(name__in=ROLE_GROUPS).values_list("name", flat=True)
        return ", ".join(user_roles) or "-"

    @admin.display(description="Mutaxassisligi")
    def specialty_display(self, obj):
        profile = getattr(obj, "doctor_profile", None)
        if not profile or not profile.specialty:
            return "-"
        return profile.specialty.name

    @admin.display(description="Bemorlar soni", ordering="patient_total")
    def patient_count(self, obj):
        return getattr(obj, "patient_total", 0)

    @admin.action(description="Set role: Admin")
    def set_role_admin(self, request, queryset):
        updated = _set_user_role(queryset, "Admin")
        self.message_user(request, f"{updated} ta foydalanuvchi Admin roliga o'tkazildi.")

    @admin.action(description="Set role: Doctor")
    def set_role_doctor(self, request, queryset):
        updated = _set_user_role(queryset, "Doctor")
        self.message_user(request, f"{updated} ta foydalanuvchi Doctor roliga o'tkazildi.")

    @admin.action(description="Set role: Viewer")
    def set_role_viewer(self, request, queryset):
        updated = _set_user_role(queryset, "Viewer")
        self.message_user(request, f"{updated} ta foydalanuvchi Viewer roliga o'tkazildi.")
