from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("team", "0008_add_isolation_center"),
    ]

    operations = [
        migrations.CreateModel(
            name="Region",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=120, unique=True, verbose_name="Hudud nomi")),
                ("code", models.CharField(blank=True, max_length=20, verbose_name="Hudud kodi")),
            ],
            options={
                "verbose_name": "Hudud",
                "verbose_name_plural": "Hududlar",
                "ordering": ["name"],
            },
        ),
        migrations.AddField(
            model_name="teammember",
            name="region",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="members",
                to="team.region",
                verbose_name="Hudud",
            ),
        ),
    ]

