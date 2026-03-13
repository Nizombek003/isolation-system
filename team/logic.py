from .models import HealthData


def calculate_risk(health):
    score = 0

    if health.temperature > 37.5:
        score += 2
    if health.symptoms:
        score += 2
    if health.close_contact:
        score += 2
    if health.chronic_disease:
        score += 1

    if score >= 5:
        return score, "Yuqori xavf - To'liq izolyatsiya"
    if score >= 3:
        return score, "O'rta xavf - Qisman izolyatsiya"
    return score, "Past xavf - Izolyatsiya talab etilmaydi"


def get_risk_statistics(queryset=None):
    queryset = queryset if queryset is not None else HealthData.objects.all()
    return {
        "low": queryset.filter(risk_level="past").count(),
        "medium": queryset.filter(risk_level="orta").count(),
        "high": queryset.filter(risk_level="yuqori").count(),
    }
