from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0007_verified_timetable_link"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="OneSchoolArchiveBatch",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("kind", models.CharField(max_length=20, choices=[
                    ("students", "SM110 Student List (Excel)"),
                    ("staff_pdf", "Whole-staff Timetable (PDF)"),
                    ("tt_alignment", "TTLineAlignmentExport (multiple files)"),
                ])),
                ("label", models.CharField(max_length=120)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("status", models.CharField(max_length=12, default="staged", choices=[
                    ("staged", "Awaiting review"), ("applied", "Applied to student directory"),
                ])),
                ("applied_at", models.DateTimeField(blank=True, null=True)),
                ("summary", models.JSONField(default=dict)),
                ("created_by", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="OneSchoolArchivedFile",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("original_name", models.CharField(max_length=180)),
                ("storage_token", models.CharField(max_length=32, unique=True)),
                ("sha256", models.CharField(max_length=64)),
                ("size", models.PositiveIntegerField()),
                ("format", models.CharField(max_length=12)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("batch", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="files", to="accounts.oneschoolarchivebatch")),
            ],
            options={"ordering": ["id"], "constraints": [
                models.UniqueConstraint(fields=["batch", "sha256"], name="unique_file_digest_in_import_batch"),
            ]},
        ),
    ]
