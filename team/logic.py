from .models import HealthData

def calculate_risk(health):
    score = 0

    if health.temperature > 37.5:
        score += 3
    if health.symptoms:
        score += 2
    if health.close_contact:
        score += 2
    if health.chronic_disease:
        score += 1

    if score >= 7:
        return score, "Yuqori xavf – To‘liq izolyatsiya"
    elif score >= 4:
        return score, "O‘rta xavf – Qisman izolyatsiya"
    else:
        return score, "Past xavf – Izolyatsiya talab etilmaydi"


def get_risk_statistics():
    low = HealthData.objects.filter(risk_score__lte=3).count()
    medium = HealthData.objects.filter(
        risk_score__gte=4,
        risk_score__lte=6
    ).count()
    high = HealthData.objects.filter(risk_score__gte=7).count()

    return {
        'low': low,
        'medium': medium,
        'high': high
    }
