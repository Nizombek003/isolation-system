import json
from datetime import timedelta

from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User
from django.contrib.auth.views import LoginView
from django.db.models import Avg, Count, Max, Q
from django.db.models.functions import TruncMonth
from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.timezone import now

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from .hospital_catalog import get_registon_hospitals_for_dashboard
from .logic import build_region_priority_map, get_risk_statistics, rank_isolation_centers
from .models import ClinicSettings, DoctorProfile, HealthData, IsolationCenter, Region, TeamMember


class CustomLoginView(LoginView):
    template_name = "team/login.html"
    redirect_authenticated_user = True

    def get_success_url(self):
        next_url = self.get_redirect_url()
        if next_url:
            return next_url

        user = self.request.user
        if is_admin(user):
            return "/admin/"
        return "/dashboard/"


def is_admin(user):
    return user.is_superuser or user.groups.filter(name="Admin").exists()


def is_doctor(user):
    return user.groups.filter(name="Doctor").exists()


def is_viewer(user):
    return user.groups.filter(name="Viewer").exists()


def can_access_patient(user, patient):
    if is_admin(user):
        return True
    if is_doctor(user):
        return patient.assigned_doctor_id == user.id
    return True


def can_edit_patient_notes(user, patient):
    if is_admin(user):
        return True
    return is_doctor(user) and patient.assigned_doctor_id == user.id


def get_base_patient_queryset(user):
    queryset = TeamMember.objects.select_related(
        "disease_type",
        "region",
        "assigned_doctor__doctor_profile__specialty",
    )
    if is_doctor(user) and not is_admin(user):
        return queryset.filter(assigned_doctor=user)
    return queryset


def apply_patient_filters(queryset, request):
    search_query = request.GET.get("q", "").strip()
    status_filter = request.GET.get("status", "").strip()
    disease_filter = request.GET.get("disease", "").strip()

    if search_query:
        queryset = queryset.filter(
            Q(full_name__icontains=search_query)
            | Q(position__icontains=search_query)
            | Q(notes__icontains=search_query)
            | Q(disease_type__name__icontains=search_query)
        )
    if status_filter:
        queryset = queryset.filter(status=status_filter)
    if disease_filter:
        queryset = queryset.filter(disease_type_id=disease_filter)

    return queryset, {
        "q": search_query,
        "status": status_filter,
        "disease": disease_filter,
    }


def get_dashboard_queryset(user, patient_queryset=None):
    queryset = HealthData.objects.select_related(
        "member__disease_type",
        "member__assigned_doctor__doctor_profile__specialty",
        "entered_by",
    )
    if patient_queryset is not None:
        return queryset.filter(member__in=patient_queryset)
    if is_doctor(user) and not is_admin(user):
        return queryset.filter(member__assigned_doctor=user)
    return queryset


def get_monthly_trend_data(queryset):
    six_months_ago = timezone.now() - timedelta(days=180)
    data = (
        queryset.filter(created_at__gte=six_months_ago)
        .annotate(month=TruncMonth("created_at"))
        .values("month")
        .annotate(avg_risk=Avg("risk_score"))
        .order_by("month")
    )

    labels = []
    values = []
    for item in data:
        labels.append(item["month"].strftime("%B"))
        values.append(round(item["avg_risk"], 2) if item["avg_risk"] else 0)
    return labels, values


def get_doctor_dashboard_context(user, patient_queryset, health_queryset):
    own_weekly_raw = (
        health_queryset.filter(created_at__gte=now() - timedelta(days=7))
        .values("risk_level")
        .annotate(count=Count("id"))
    )
    own_weekly_stats = {"past": 0, "orta": 0, "yuqori": 0}
    for item in own_weekly_raw:
        if item["risk_level"]:
            own_weekly_stats[item["risk_level"]] = item["count"]

    return {
        "doctor_focus": {
            "profile": getattr(user, "doctor_profile", None),
            "patient_total": patient_queryset.count(),
            "active_patients": patient_queryset.exclude(status="barqaror").count(),
            "high_risk_patients": health_queryset.filter(risk_level="yuqori").values("member_id").distinct().count(),
            "latest_updates": health_queryset[:5],
            "status_breakdown": list(
                patient_queryset.values("status").annotate(total=Count("id")).order_by("status")
            ),
            "weekly_stats": own_weekly_stats,
        }
    }


@user_passes_test(lambda u: is_admin(u) or is_doctor(u))
def add_health(request):
    return redirect("/admin/team/healthdata/add/")


@login_required
def dashboard(request):
    clinic = ClinicSettings.objects.first()
    patient_queryset, active_filters = apply_patient_filters(get_base_patient_queryset(request.user), request)
    dashboard_queryset = get_dashboard_queryset(request.user, patient_queryset)
    stats = get_risk_statistics(dashboard_queryset)
    last_week = now() - timedelta(days=7)

    weekly_raw = (
        dashboard_queryset.filter(created_at__gte=last_week)
        .values("risk_level")
        .annotate(count=Count("id"))
    )
    weekly_stats = {"past": 0, "orta": 0, "yuqori": 0}
    for item in weekly_raw:
        if item["risk_level"]:
            weekly_stats[item["risk_level"]] = item["count"]

    patient_summary = {
        "total": patient_queryset.count(),
        "assigned": patient_queryset.exclude(assigned_doctor__isnull=True).count(),
        "active": patient_queryset.exclude(status="barqaror").count(),
        "doctors": DoctorProfile.objects.count(),
    }

    region_stats = list(
        patient_queryset.exclude(region__isnull=True)
        .values("region__name")
        .annotate(total=Count("id"))
        .order_by("-total", "region__name")[:5]
    )

    disease_stats = list(
        patient_queryset.exclude(disease_type__isnull=True)
        .values("disease_type__name")
        .annotate(total=Count("id"))
        .order_by("-total", "disease_type__name")[:5]
    )

    doctor_load = list(
        patient_queryset.exclude(assigned_doctor__isnull=True)
        .values(
            "assigned_doctor__username",
            "assigned_doctor__doctor_profile__specialty__name",
        )
        .annotate(total=Count("id"))
        .order_by("-total", "assigned_doctor__username")[:5]
    )

    recent_cases = dashboard_queryset[:6]

    high_risk_region_rows = list(
        dashboard_queryset.filter(
            risk_level="yuqori",
            member__region__isnull=False,
        )
        .values("member__region_id")
        .annotate(total=Count("member_id", distinct=True))
    )
    region_priority_map = build_region_priority_map(high_risk_region_rows)
    center_rankings = rank_isolation_centers(
        IsolationCenter.objects.filter(is_active=True).select_related("region"),
        region_priority_map,
    )[:5]
    isolation_centers = [item["center"] for item in center_rankings]
    if stats["high"] > 0:
        recommendation = "Yuqori xavf aniqlangan. To'liq izolyatsiya va shifokor nazorati tavsiya etiladi."
        if center_rankings:
            top_item = center_rankings[0]
            recommendation += (
                f" Fuzzy MCDM bo'yicha eng mos markaz: {top_item['center'].name} "
                f"({top_item['score']} ball)."
            )
            recommendation += " Yuqori xavfli bemorlarni izolyatsiya markazlariga yo'naltirish mumkin (Admin -> Izolyatsiya markazlari)."
    elif stats["medium"] > 0:
        recommendation = "O'rta xavf holatlari bor. Masofaviy ish va qayta ko'rik tavsiya etiladi."
    else:
        recommendation = "Holat barqaror. Rejalashtirilgan monitoringni davom ettiring."

    context = {
        "isolation_centers": isolation_centers,
        "center_rankings": center_rankings,
        "stats": stats,
        "weekly_stats": weekly_stats,
        "recommendation": recommendation,
        "clinic": clinic,
        "patient_summary": patient_summary,
        "region_stats": region_stats,
        "disease_stats": disease_stats,
        "doctor_load": doctor_load,
        "recent_cases": recent_cases,
        "registon_hospitals": get_registon_hospitals_for_dashboard(),
        "is_doctor_dashboard": is_doctor(request.user) and not is_admin(request.user),
        "active_filters": active_filters,
        "disease_options": patient_queryset.model.objects.exclude(disease_type__isnull=True).values_list("disease_type__id", "disease_type__name").distinct().order_by("disease_type__name"),
        "status_options": TeamMember.STATUS_CHOICES,
    }
    if context["is_doctor_dashboard"]:
        context.update(get_doctor_dashboard_context(request.user, patient_queryset, dashboard_queryset))

    return render(request, "team/dashboard.html", context)


@login_required
def monthly_trend(request):
    patient_queryset, _ = apply_patient_filters(get_base_patient_queryset(request.user), request)
    labels, values = get_monthly_trend_data(get_dashboard_queryset(request.user, patient_queryset))
    return JsonResponse({"labels": labels, "values": values})


@login_required
def patient_detail(request, member_id):
    patient = get_object_or_404(
        TeamMember.objects.select_related("disease_type", "assigned_doctor__doctor_profile__specialty"),
        pk=member_id,
    )
    if not can_access_patient(request.user, patient):
        raise Http404("Bemor topilmadi.")

    if request.method == "POST":
        if not can_edit_patient_notes(request.user, patient):
            raise Http404("Bemor topilmadi.")
        patient.notes = request.POST.get("notes", "").strip()
        patient.save(update_fields=["notes"])
        return redirect(f"/patients/{patient.id}/?saved=1")

    history_queryset = HealthData.objects.filter(member=patient).select_related("entered_by")
    latest_entry = history_queryset.first()
    history_chart = list(history_queryset.order_by("created_at").values("created_at", "risk_score", "temperature"))

    history_labels = [item["created_at"].strftime("%d.%m") for item in history_chart]
    history_scores = [item["risk_score"] or 0 for item in history_chart]
    history_temperatures = [float(item["temperature"]) for item in history_chart]

    status_timeline = list(
        history_queryset.values("risk_level")
        .annotate(total=Count("id"), latest_at=Max("created_at"))
        .order_by("-latest_at")
    )

    return render(
        request,
        "team/patient_detail.html",
        {
            "patient": patient,
            "latest_entry": latest_entry,
            "history": history_queryset[:12],
            "status_timeline": status_timeline,
            "history_labels_json": json.dumps(history_labels),
            "history_scores_json": json.dumps(history_scores),
            "history_temperatures_json": json.dumps(history_temperatures),
            "can_edit_notes": can_edit_patient_notes(request.user, patient),
            "note_saved": request.GET.get("saved") == "1",
        },
    )


@login_required
def generate_report(request):
    clinic = ClinicSettings.objects.first()
    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = 'attachment; filename="sogliq_hisobot.pdf"'

    doc = SimpleDocTemplate(response, pagesize=A4)
    elements = []
    styles = getSampleStyleSheet()

    title = clinic.name if clinic else "Jamoat salomatligi va izolyatsiya tavsiyalari — sog'liq hisoboti"
    elements.append(Paragraph(f"<b>{title}</b>", styles["Title"]))
    elements.append(Spacer(1, 0.3 * inch))
    elements.append(Paragraph(f"Sana: {now().date()}", styles["Normal"]))
    elements.append(Spacer(1, 0.3 * inch))

    patient_queryset, _ = apply_patient_filters(get_base_patient_queryset(request.user), request)
    queryset = get_dashboard_queryset(request.user, patient_queryset)
    stats = get_risk_statistics(queryset)

    elements.append(Paragraph("<b>Umumiy statistika:</b>", styles["Heading2"]))
    elements.append(Spacer(1, 0.2 * inch))
    elements.append(Paragraph(f"Past xavf: {stats['low']}", styles["Normal"]))
    elements.append(Paragraph(f"O'rta xavf: {stats['medium']}", styles["Normal"]))
    elements.append(Paragraph(f"Yuqori xavf: {stats['high']}", styles["Normal"]))
    elements.append(Paragraph(f"Jami bemorlar: {patient_queryset.count()}", styles["Normal"]))
    elements.append(Spacer(1, 0.4 * inch))

    elements.append(Paragraph("<b>So'nggi kuzatuvlar:</b>", styles["Heading2"]))
    elements.append(Spacer(1, 0.2 * inch))

    data = [["Bemor", "Kasallik", "Shifokor", "Harorat", "Xavf", "Ball"]]
    for obj in queryset[:15]:
        data.append(
            [
                obj.member.full_name,
                obj.member.disease_type.name if obj.member.disease_type else "-",
                obj.member.assigned_doctor.get_username() if obj.member.assigned_doctor else "-",
                str(obj.temperature),
                obj.get_risk_level_display() or "-",
                str(obj.risk_score or "-"),
            ]
        )

    table = Table(data, repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.darkblue),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("GRID", (0, 0), (-1, -1), 1, colors.black),
                ("ALIGN", (1, 1), (-1, -1), "CENTER"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
            ]
        )
    )

    elements.append(table)
    doc.build(elements)
    return response


 