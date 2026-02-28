from django.db import models
from django.utils.translation import gettext_lazy as _


# 👥 Jamoa a'zosi modeli
class TeamMember(models.Model):
    full_name = models.CharField(_("Ism familiya"), max_length=100)
    age = models.IntegerField(_("Yosh"))
    position = models.CharField(_("Lavozim"), max_length=100)

    class Meta:
        verbose_name = _("Jamoa a'zosi")
        verbose_name_plural = _("Jamoa a'zolari")

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


# 🏥 Sog‘liq ma'lumotlari modeli
class HealthData(models.Model):

    RISK_CHOICES = [
        ('past', _("Past xavf")),
        ('orta', _("O‘rta xavf")),
        ('yuqori', _("Yuqori xavf")),
    ]

    member = models.ForeignKey(
        TeamMember,
        on_delete=models.CASCADE,
        verbose_name=_("Xodim")
    )

    temperature = models.FloatField(_("Harorat (°C)"))
    symptoms = models.BooleanField(_("Simptomlar mavjud"), default=False)
    close_contact = models.BooleanField(_("Kasallangan bilan yaqin aloqada bo‘lgan"), default=False)
    chronic_disease = models.BooleanField(_("Surunkali kasalligi bor"), default=False)

    risk_score = models.IntegerField(_("Xavf balli"), null=True, blank=True)

    risk_level = models.CharField(
        _("Xavf darajasi"),
        max_length=10,
        choices=RISK_CHOICES,
        null=True,
        blank=True
    )

    recommendation = models.CharField(
        _("Tavsiya"),
        max_length=255,
        null=True,
        blank=True
    )

    created_at = models.DateTimeField(_("Yaratilgan sana"), auto_now_add=True)

    class Meta:
        verbose_name = _("Sog‘liq ma'lumoti")
        verbose_name_plural = _("Sog‘liq ma'lumotlari")
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        """
        Har safar saqlanganda xavf avtomatik hisoblanadi
        """

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

        # Xavf darajasini aniqlash
        if score >= 5:
            self.risk_level = 'yuqori'
            self.recommendation = "To‘liq izolyatsiya tavsiya etiladi."
        elif score >= 3:
            self.risk_level = 'orta'
            self.recommendation = "Masofaviy ish va qisman izolyatsiya tavsiya etiladi."
        else:
            self.risk_level = 'past'
            self.recommendation = "Holat barqaror, izolyatsiya talab etilmaydi."

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.member.full_name} - {self.get_risk_level_display()}"
