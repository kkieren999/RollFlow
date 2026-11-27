from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0014_staff_access_grant"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]
    operations = [
        migrations.CreateModel(
            name="AttendanceRoll",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("lesson_date", models.DateField()),
                ("class_code", models.CharField(max_length=30)),
                ("period", models.CharField(max_length=50)),
                ("start", models.CharField(max_length=5)),
                ("end", models.CharField(max_length=5)),
                ("roster", models.JSONField()),
                ("marks", models.JSONField(default=dict)),
                ("revision", models.PositiveIntegerField(default=1)),
                ("submitted_at", models.DateTimeField(blank=True, null=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("publication", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to="accounts.connectedschoolpublication")),
                ("teacher", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name="AttendanceRevision",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("revision", models.PositiveIntegerField()),
                ("action", models.CharField(max_length=12)),
                ("marks", models.JSONField()),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("actor", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL)),
                ("roll", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="history", to="accounts.attendanceroll")),
            ],
        ),
        migrations.AddConstraint(model_name="attendanceroll", constraint=models.UniqueConstraint(
            fields=("lesson_date", "class_code", "period", "start"), name="unique_dated_attendance_lesson")),
        migrations.AddConstraint(model_name="attendancerevision", constraint=models.UniqueConstraint(
            fields=("roll", "revision"), name="unique_attendance_revision")),
    ]
