from django.shortcuts import render, redirect
from django.http import HttpResponse, JsonResponse
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.views import LoginView
from django.db.models import Count, Avg
from django.db.models.functions import TruncMonth
from django.utils.timezone import now
from django.utils import timezone
from datetime import timedelta

from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.lib.pagesizes import A4

from .logic import get_risk_statistics
from .models import HealthData, ClinicSettings


# ==================================================
# CUSTOM LOGIN
# ==================================================

class CustomLoginView(LoginView):
    template_name = 'team/login.html'


# ==================================================
# ROLE CHECK FUNCTIONS
# ==================================================

def is_admin(user):
    return user.is_superuser or user.groups.filter(name='Admin').exists()

def is_doctor(user):
    return user.groups.filter(name='Doctor').exists()

def is_viewer(user):
    return user.groups.filter(name='Viewer').exists()


# ==================================================
# ADD HEALTH (Admin + Doctor only)
# ==================================================

@user_passes_test(lambda u: is_admin(u) or is_doctor(u))
def add_health(request):
    return redirect('/admin/team/healthdata/add/')


# ==================================================
# DASHBOARD
# ==================================================

@login_required
def dashboard(request):

    clinic = ClinicSettings.objects.first()

    if not (is_admin(request.user) or is_doctor(request.user) or is_viewer(request.user)):
        return redirect('login')

    stats = get_risk_statistics()

    last_week = now() - timedelta(days=7)

    weekly_raw = (
        HealthData.objects
        .filter(created_at__gte=last_week)
        .values('risk_level')
        .annotate(count=Count('id'))
    )

    weekly_stats = {'past': 0, 'orta': 0, 'yuqori': 0}

    for item in weekly_raw:
        if item['risk_level']:
            weekly_stats[item['risk_level']] = item['count']

    if stats['high'] > 0:
        recommendation = "Yuqori xavf aniqlangan. To‘liq izolyatsiya tavsiya etiladi."
    elif stats['medium'] > 0:
        recommendation = "O‘rta xavf mavjud. Masofaviy ish tavsiya etiladi."
    else:
        recommendation = "Holat barqaror."

    return render(request, 'team/dashboard.html', {
        'stats': stats,
        'weekly_stats': weekly_stats,
        'recommendation': recommendation,
        'clinic': clinic,
    })


# ==================================================
# MONTHLY TREND
# ==================================================

@login_required
def monthly_trend(request):

    six_months_ago = timezone.now() - timedelta(days=180)

    data = (
        HealthData.objects
        .filter(created_at__gte=six_months_ago)
        .annotate(month=TruncMonth('created_at'))
        .values('month')
        .annotate(avg_risk=Avg('risk_score'))
        .order_by('month')
    )

    labels = []
    values = []

    for item in data:
        labels.append(item['month'].strftime("%B"))
        values.append(round(item['avg_risk'], 2) if item['avg_risk'] else 0)

    return JsonResponse({
        "labels": labels,
        "values": values
    })


# ==================================================
# PDF HISOBOT
# ==================================================

@login_required
def generate_report(request):

    clinic = ClinicSettings.objects.first()

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="sogliq_hisobot.pdf"'

    doc = SimpleDocTemplate(response, pagesize=A4)
    elements = []
    styles = getSampleStyleSheet()

    title = clinic.name if clinic else "Jamoa Sog‘liq Monitoring Hisoboti"
    elements.append(Paragraph(f"<b>{title}</b>", styles['Title']))
    elements.append(Spacer(1, 0.3 * inch))

    elements.append(Paragraph(f"Sana: {now().date()}", styles['Normal']))
    elements.append(Spacer(1, 0.3 * inch))

    stats = get_risk_statistics()

    elements.append(Paragraph("<b>Umumiy statistika:</b>", styles['Heading2']))
    elements.append(Spacer(1, 0.2 * inch))

    elements.append(Paragraph(f"Past xavf: {stats['low']}", styles['Normal']))
    elements.append(Paragraph(f"O‘rta xavf: {stats['medium']}", styles['Normal']))
    elements.append(Paragraph(f"Yuqori xavf: {stats['high']}", styles['Normal']))
    elements.append(Spacer(1, 0.4 * inch))

    elements.append(Paragraph("<b>Xodimlar ro‘yxati:</b>", styles['Heading2']))
    elements.append(Spacer(1, 0.2 * inch))

    data = [['Xodim', 'Harorat', 'Xavf darajasi', 'Ball']]

    queryset = HealthData.objects.select_related('member').all()

    for obj in queryset:
        data.append([
            obj.member.full_name,
            str(obj.temperature),
            obj.get_risk_level_display() or "-",
            str(obj.risk_score or "-")
        ])

    table = Table(data, repeatRows=1)

    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('ALIGN', (1, 1), (-1, -1), 'CENTER'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
    ]))

    elements.append(table)

    doc.build(elements)
    return response
from django.contrib.auth.models import User

def create_admin(request):
    if not User.objects.filter(username="admin").exists():
        User.objects.create_superuser(
            username="admin",
            email="admin@example.com",
            password="12345678"
        )
        return HttpResponse("Superuser yaratildi!")
    return HttpResponse("Superuser mavjud.")