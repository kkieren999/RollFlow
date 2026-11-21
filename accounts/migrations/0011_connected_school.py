from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0010_oneschool_timetable_evidence"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]
    operations = [
        migrations.CreateModel(
            name="ConnectedStaffMapping",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("staff_code", models.CharField(max_length=40, unique=True)),
                ("verified_staff_id", models.CharField(max_length=40)),
                ("verified_at", models.DateTimeField(auto_now=True)),
                ("profile", models.OneToOneField(on_delete=django.db.models.deletion.PROTECT, related_name="connected_mapping", to="accounts.staffprofile")),
                ("verified_by", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name="ConnectedSchoolPublication",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=100)),
                ("starts", models.DateField()),
                ("ends", models.DateField()),
                ("active", models.BooleanField(default=True)),
                ("source_batches", models.JSONField(default=dict)),
                ("snapshot", models.JSONField(default=dict)),
                ("digest", models.CharField(max_length=64)),
                ("published_at", models.DateTimeField(auto_now_add=True)),
                ("published_by", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "ordering": ["-published_at", "-pk"],
                "constraints": [
                    models.UniqueConstraint(fields=["active"], condition=models.Q(active=True), name="single_active_connected_school"),
                    models.CheckConstraint(condition=models.Q(ends__gte=models.F("starts")), name="connected_school_date_order"),
                ],
            },
        ),
    ]
