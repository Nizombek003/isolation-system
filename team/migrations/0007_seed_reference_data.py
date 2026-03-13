from django.db import migrations


def seed_reference_data(apps, schema_editor):
    DiseaseType = apps.get_model("team", "DiseaseType")
    DoctorSpecialty = apps.get_model("team", "DoctorSpecialty")

    for name in ["Terapevt", "Kardiolog", "Pediatr", "Nevrolog", "Infeksionist"]:
        DoctorSpecialty.objects.get_or_create(name=name)

    diseases = [
        ("Gripp", True),
        ("COVID-19", True),
        ("Bronxit", False),
        ("Pnevmoniya", True),
        ("Allergiya", False),
    ]
    for name, isolation_required in diseases:
        DiseaseType.objects.get_or_create(
            name=name,
            defaults={"isolation_required": isolation_required},
        )


def remove_reference_data(apps, schema_editor):
    DiseaseType = apps.get_model("team", "DiseaseType")
    DoctorSpecialty = apps.get_model("team", "DoctorSpecialty")

    DiseaseType.objects.filter(name__in=["Gripp", "COVID-19", "Bronxit", "Pnevmoniya", "Allergiya"]).delete()
    DoctorSpecialty.objects.filter(name__in=["Terapevt", "Kardiolog", "Pediatr", "Nevrolog", "Infeksionist"]).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("team", "0006_diseasetype_doctorspecialty_alter_healthdata_options_and_more"),
    ]

    operations = [
        migrations.RunPython(seed_reference_data, remove_reference_data),
    ]
