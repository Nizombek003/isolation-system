"""
Ko'p mezonli va noaniq (fuzzy) xavf baholash — BMI topshiriq varaqasidagi
«noaniq ko'p mezonli qarorlarni qabul qilish tizimi» talabiga mos.

Mezonlar:
- harorat (temperature),
- simptomlar (symptoms),
- yuqumli bilan yaqin aloqa (close_contact),
- surunkali kasallik (chronic_disease).

Har bir mezon uchun [0, 1] oralig'ida fuzzy daraja hisoblanadi va
og'irliklangan yig'indi ko'rinishida umumiy xavf darajasi olinadi.
"""
from .models import HealthData, IsolationCenter


def _temp_membership(value: float | None) -> float:
    """
    Harorat uchun fuzzy a'zolik funksiyasi:
    - 36.5°C va undan past: 0 (xavf yo'q)
    - 39°C va undan yuqori: 1 (yuqori xavf)
    - oralig'ida chiziqli oshish.
    """
    if value is None:
        return 0.0
    if value <= 36.5:
        return 0.0
    if value >= 39.0:
        return 1.0
    return (value - 36.5) / (39.0 - 36.5)


def _bool_membership(flag: bool, high: float = 1.0) -> float:
    """
    Boolean mezonlar uchun oddiy fuzzy:
    - True => berilgan yuqori daraja (masalan, 1.0 yoki 0.8)
    - False => 0
    """
    return float(high if flag else 0.0)


def _aggregate_memberships(temperature: float | None, symptoms: bool, close_contact: bool, chronic_disease: bool) -> float:
    """
    Og'irliklangan ko'p mezonli fuzzy agregatsiya.
    Og'irliklar:
    - harorat: 0.4
    - simptomlar: 0.3
    - yaqin aloqa: 0.2
    - surunkali kasallik: 0.1
    """
    w_temp = 0.4
    w_symptoms = 0.3
    w_contact = 0.2
    w_chronic = 0.1

    mu_temp = _temp_membership(temperature)
    mu_symptoms = _bool_membership(symptoms, high=1.0)
    mu_contact = _bool_membership(close_contact, high=0.9)
    mu_chronic = _bool_membership(chronic_disease, high=0.7)

    return (
        w_temp * mu_temp
        + w_symptoms * mu_symptoms
        + w_contact * mu_contact
        + w_chronic * mu_chronic
    )


def _level_from_score(score: int) -> str:
    """
    Diskret xavf darajasi:
    - 0–3: past
    - 4–6: o'rta
    - 7–10: yuqori
    """
    if score >= 7:
        return "yuqori"
    if score >= 4:
        return "orta"
    return "past"


def calculate_risk(health: HealthData) -> tuple[int, str, str]:
    """
    Ko'p mezonli fuzzy agregatsiya asosida:
    - risk_score (0–10 butun son),
    - risk_level (past/orta/yuqori),
    - matnli tavsiya qaytaradi.
    """
    fuzzy_value = _aggregate_memberships(
        temperature=getattr(health, "temperature", None),
        symptoms=bool(getattr(health, "symptoms", False)),
        close_contact=bool(getattr(health, "close_contact", False)),
        chronic_disease=bool(getattr(health, "chronic_disease", False)),
    )

    score = int(round(fuzzy_value * 10))
    level = _level_from_score(score)

    if level == "yuqori":
        recommendation = "Yuqori xavf - to'liq izolyatsiya va shifokor nazorati tavsiya etiladi."
    elif level == "orta":
        recommendation = "O'rta xavf - masofaviy ish, cheklangan kontakt va kuzatuv tavsiya etiladi."
    else:
        recommendation = "Past xavf - holat barqaror, oddiy profilaktika va muntazam monitoring kifoya."

    return score, level, recommendation


def get_risk_statistics(queryset=None):
    queryset = queryset if queryset is not None else HealthData.objects.all()
    return {
        "low": queryset.filter(risk_level="past").count(),
        "medium": queryset.filter(risk_level="orta").count(),
        "high": queryset.filter(risk_level="yuqori").count(),
    }


def _clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(value, maximum))


def _normalize_benefit(value: float, min_value: float, max_value: float) -> float:
    if max_value <= min_value:
        return 0.0
    return _clamp((value - min_value) / (max_value - min_value), 0.0, 1.0)


def _normalize_cost(value: float, min_value: float, max_value: float) -> float:
    if max_value <= min_value:
        return 0.0
    return _clamp((max_value - value) / (max_value - min_value), 0.0, 1.0)


def build_region_priority_map(rows):
    """
    rows format:
    [
        {"member__region_id": <id>, "total": <int>},
        ...
    ]
    """
    total = sum(int(item.get("total", 0) or 0) for item in rows)
    if total <= 0:
        return {}

    result = {}
    for item in rows:
        region_id = item.get("member__region_id")
        if not region_id:
            continue
        count = int(item.get("total", 0) or 0)
        result[region_id] = round(count / total, 4)
    return result


def rank_isolation_centers(centers, region_priority_map=None):
    """
    Fuzzy MCDM ranking for isolation-center selection.
    Weighted criteria:
    - availability (1 - occupancy): 0.35
    - readiness score: 0.25
    - access time (cost): 0.20
    - infrastructure score: 0.10
    - region priority (high-risk density): 0.10
    """
    region_priority_map = region_priority_map or {}
    rankings = []

    for center in centers:
        occupancy = float(getattr(center, "occupancy_rate", 0) or 0)
        readiness = float(getattr(center, "readiness_score", 0) or 0)
        access_time = float(getattr(center, "travel_time_minutes", 0) or 0)
        infrastructure = float(getattr(center, "infrastructure_score", 0) or 0)
        region_priority = float(region_priority_map.get(center.region_id, 0.0))

        availability_mu = _normalize_benefit(100.0 - occupancy, 0.0, 100.0)
        readiness_mu = _normalize_benefit(readiness, 0.0, 10.0)
        access_mu = _normalize_cost(access_time, 10.0, 120.0)
        infrastructure_mu = _normalize_benefit(infrastructure, 0.0, 10.0)
        region_mu = _clamp(region_priority, 0.0, 1.0)

        fuzzy_value = (
            0.35 * availability_mu
            + 0.25 * readiness_mu
            + 0.20 * access_mu
            + 0.10 * infrastructure_mu
            + 0.10 * region_mu
        )
        score = round(fuzzy_value * 100, 2)

        if score >= 75:
            label = "A'lo mos"
        elif score >= 55:
            label = "Yaxshi mos"
        elif score >= 40:
            label = "Qoniqarli"
        else:
            label = "Past ustuvorlik"

        rankings.append(
            {
                "center": center,
                "score": score,
                "label": label,
                "availability_mu": round(availability_mu, 3),
                "readiness_mu": round(readiness_mu, 3),
                "access_mu": round(access_mu, 3),
                "infrastructure_mu": round(infrastructure_mu, 3),
                "region_mu": round(region_mu, 3),
            }
        )

    rankings.sort(key=lambda row: (-row["score"], row["center"].name.lower()))
    return rankings
