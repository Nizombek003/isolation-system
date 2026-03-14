# Jamoat salomatligi va izolyatsiya tavsiyalari tizimi

**Bitiruv malakaviy ishi (BMI)** — TATU Samarqand filiali, «Kompyuter injiniringi (AT servis)» yo‘nalishi.

## BMI mavzusi

*Jamoat salomatligi va barqarorligini oshirishda jamoani izolyatsiya qilishga tavsiyalar beruvchi axborot tizimini yaratish.*

Tizim topshiriq varaqasidagi talablarga mos ravishda quyidagilarni qo‘llab-quvvatlaydi:

- **Yuqumli kasalliklar va favqulodda vaziyatlarga tayyorgarlik** — bemorlarning sog‘liq ma’lumotlari asosida xavf baholash va izolyatsiya tavsiyalari.
- **Noaniq ko‘p mezonli qarorlarni qabul qilish (fuzzy MCDM)** — harorat, simptomlar, yaqin aloqa va surunkali kasallik kabi bir nechta mezonlar bo‘yicha noaniq (fuzzy) xavf balli va darajasi hisoblanishi; natijada past / o‘rta / yuqori xavf va tegishli tavsiyalar beriladi.
- **Izolyatsiya markazlari** — markazlarni ro‘yxatga olish va yuqori xavf holatlarida tegishli markazga yo‘naltirish imkoniyati (operatsion samaradorlik va jamiyat barqarorligini oshirish maqsadida).
- **Tibbiy xizmat sifati** — shifokor–bemor biriktirish, sog‘liq yozuvlari, PDF hisobotlar va dashboard orqali monitoring.

## Texnologiyalar

- **Backend:** Django 5.x
- **Admin:** django-unfold
- **Hisobot:** ReportLab (PDF)

## Ishga tushirish

```bash
python -m venv .venv
.venv\Scripts\activate   # Windows
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

Birinchi marta superuser yaratish: `/create-admin/` (login: `admin`, parol: `12345678`) yoki `python manage.py createsuperuser`.

## Tizim tarkibi (qisqacha)

- **Bemorlar (TeamMember)** — ism, yosh, kasallik turi, mas’ul shifokor, status (kuzatuvda / davolanishda / barqaror).
- **Sog‘liq ma’lumotlari (HealthData)** — harorat, simptomlar, yaqin aloqa, surunkali kasallik; tizim tomonidan **ko‘p mezonli** va **noaniq (fuzzy)** xavf balli va darajasi hisoblanadi, tavsiya avtomatik beriladi.
- **Izolyatsiya markazlari (IsolationCenter)** — nomi, manzil, sig‘im; yuqori xavf tavsiyalarida ko‘rsatilishi mumkin.
- **Shifokorlar va mutaxassisliklar** — DoctorProfile, DoctorSpecialty; Admin / Doctor / Viewer rollari.

## Adabiyotlar (topshiriq varaqasidan)

Tizimda qo‘llaniladigan yondashuvlar va adabiyotlar: Fuzzy AHP, kasalxona/joylashuv tanlashda ikki bosqichli fuzzy ko‘p mezonli qaror qabul qilish, tibbiy tashxisda intuitionistic fuzzy to‘plamlar, sog‘liqni saqlash ma’lumotlari boshqaruvi va monitoring.
