from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class DoctorSpecialty(models.Model):
    name = models.CharField(_("Mutaxassislik nomi"), max_length=100, unique=True)
    description = models.TextField(_("Izoh"), blank=True)

    class Meta:
        verbose_name = _("Shifokor mutaxassisligi")
        verbose_name_plural = _("Shifokor mutaxassisliklari")
        ordering = ["name"]

    def __str__(self):
        return self.name


class DiseaseType(models.Model):
    name = models.CharField(_("Kasallik turi"), max_length=120, unique=True)
    description = models.TextField(_("Izoh"), blank=True)
    isolation_required = models.BooleanField(_("Izolyatsiya kerak"), default=False)

    class Meta:
        verbose_name = _("Kasallik turi")
        verbose_name_plural = _("Kasallik turlari")
        ordering = ["name"]

    def __str__(self):
        return self.name


class DoctorProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="doctor_profile",
        verbose_name=_("Foydalanuvchi"),
    )
    specialty = models.ForeignKey(
        DoctorSpecialty,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="doctors",
        verbose_name=_("Mutaxassisligi"),
    )
    room = models.CharField(_("Xona"), max_length=50, blank=True)

    class Meta:
        verbose_name = _("Shifokor profili")
        verbose_name_plural = _("Shifokor profillari")
        ordering = ["user__username"]

    def __str__(self):
        specialty = self.specialty.name if self.specialty else _("Biriktirilmagan")
        return f"{self.user.get_username()} - {specialty}"


class TeamMember(models.Model):
    STATUS_CHOICES = [
        ("kuzatuv", _("Kuzatuvda")),
        ("davolanish", _("Davolanishda")),
        ("barqaror", _("Barqaror")),
    ]

    full_name = models.CharField(_("Ism familiya"), max_length=100)
    age = models.IntegerField(_("Yosh"))
    position = models.CharField(_("Lavozim"), max_length=100)
    disease_type = models.ForeignKey(
        DiseaseType,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="patients",
        verbose_name=_("Kasallik turi"),
    )
    assigned_doctor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="patients",
        verbose_name=_("Mas'ul shifokor"),
    )
    status = models.CharField(
        _("Holati"),
        max_length=20,
        choices=STATUS_CHOICES,
        default="kuzatuv",
    )
    notes = models.TextField(_("Shifokor izohi"), blank=True)

    class Meta:
        verbose_name = _("Bemor")
        verbose_name_plural = _("Bemorlar")
        ordering = ["full_name"]

    def __str__(self):
        return self.full_name


class ClinicSettings(models.Model):
    name = models.CharField("Klinika nomi", max_length=255)
    address = models.TextField("Manzil", blank=True)
    phone = models.CharField("Telefon", max_length=50, blank=True)

    class Meta:
        verbose_name = "Klinika sozlamasi"
        verbose_name_plural = "Klinika sozlamalari"

    def __str__(self):
        return self.name


class HealthData(models.Model):
    RISK_CHOICES = [
        ("past", _("Past xavf")),
        ("orta", _("O'rta xavf")),
        ("yuqori", _("Yuqori xavf")),
    ]

    member = models.ForeignKey(
        TeamMember,
        on_delete=models.CASCADE,
        verbose_name=_("Bemor"),
    )
    entered_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="entered_health_records",
        verbose_name=_("Ma'lumotni kiritgan"),
    )
    temperature = models.FloatField(_("Harorat (C)"))
    symptoms = models.BooleanField(_("Simptomlar mavjud"), default=False)
    close_contact = models.BooleanField(_("Kasallangan bilan yaqin aloqada bo'lgan"), default=False)
    chronic_disease = models.BooleanField(_("Surunkali kasalligi bor"), default=False)
    risk_score = models.IntegerField(_("Xavf balli"), null=True, blank=True)
    risk_level = models.CharField(
        _("Xavf darajasi"),
        max_length=10,
        choices=RISK_CHOICES,
        null=True,
        blank=True,
    )
    recommendation = models.CharField(
        _("Tavsiya"),
        max_length=255,
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(_("Yaratilgan sana"), auto_now_add=True)

    class Meta:
        verbose_name = _("Sog'liq ma'lumoti")
        verbose_name_plural = _("Sog'liq ma'lumotlari")
        ordering = ["-created_at"]

    def save(self, *args, **kwargs):
        score = 0

        if self.temperature and self.temperature > 37.5:
            score += 2

        if self.symptoms:
            score += 2

        if self.close_contact:
            score += 2

        if self.chronic_disease:
            score += 1

        self.risk_score = score

        if score >= 5:
            self.risk_level = "yuqori"
            self.recommendation = "To'liq izolyatsiya tavsiya etiladi."
        elif score >= 3:
            self.risk_level = "orta"
            self.recommendation = "Masofaviy ish va qisman izolyatsiya tavsiya etiladi."
        else:
            self.risk_level = "past"
            self.recommendation = "Holat barqaror, izolyatsiya talab etilmaydi."

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.member.full_name} - {self.get_risk_level_display()}"
