"""
Ko'p mezonli va noaniq (fuzzy) xavf baholash — BMI topshiriq varaqasidagi
«noaniq ko'p mezonli qarorlarni qabul qilish tizimi» talabiga mos.
Mezonlar: harorat, simptomlar, yaqin aloqa (kasallangan bilan), surunkali kasallik.
"""
from .models import HealthData


def _fuzzy_membership(score):
    """
    Xavf balli uchun oddiy trapezoidal/o'rtacha daraja (0–7) bo'yicha
    noaniq (fuzzy) daraja: past / orta / yuqori.
    """
    if score >= 5:
        return "yuqori"
    if score >= 3:
        return "orta"
    return "past"


def calculate_risk(health):
    """Ko'p mezonli (4 ta mezon) asosida xavf balli va tavsiya."""
    score = 0

    if health.temperature > 37.5:
        score += 2
    if health.symptoms:
        score += 2
    if health.close_contact:
        score += 2
    if health.chronic_disease:
        score += 1

    level = _fuzzy_membership(score)
    if level == "yuqori":
        return score, "Yuqori xavf - To'liq izolyatsiya"
    if level == "orta":
        return score, "O'rta xavf - Qisman izolyatsiya"
    return score, "Past xavf - Izolyatsiya talab etilmaydi"


def get_risk_statistics(queryset=None):
    queryset = queryset if queryset is not None else HealthData.objects.all()
    return {
        "low": queryset.filter(risk_level="past").count(),
        "medium": queryset.filter(risk_level="orta").count(),
        "high": queryset.filter(risk_level="yuqori").count(),
    }
