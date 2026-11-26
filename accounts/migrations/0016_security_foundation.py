from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0015_attendance_foundation"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]
    operations = [
        migrations.CreateModel(name="RoleTemplate", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("name", models.CharField(max_length=80, unique=True)),
            ("scope", models.CharField(max_length=12)),
            ("capabilities", models.JSONField(default=list)),
            ("active", models.BooleanField(default=True)),
            ("created_at", models.DateTimeField(auto_now_add=True)),
            ("created_by", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL)),
        ]),
        migrations.CreateModel(name="AccessAudit", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("action", models.CharField(max_length=40)),
            ("before", models.JSONField(default=dict)),
            ("after", models.JSONField(default=dict)),
            ("created_at", models.DateTimeField(auto_now_add=True)),
            ("actor", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="+", to=settings.AUTH_USER_MODEL)),
            ("target", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="+", to=settings.AUTH_USER_MODEL)),
        ]),
        migrations.AddField(model_name="staffaccessgrant", name="template",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, to="accounts.roletemplate")),
        migrations.AddField(model_name="staffaccessgrant", name="starts_at", field=models.DateTimeField(blank=True, null=True)),
        migrations.AddField(model_name="staffaccessgrant", name="expires_at", field=models.DateTimeField(blank=True, null=True)),
        migrations.AddConstraint(model_name="staffaccessgrant", constraint=models.CheckConstraint(
            condition=models.Q(starts_at__isnull=True) | models.Q(expires_at__isnull=True) | models.Q(expires_at__gt=models.F("starts_at")),
            name="staff_grant_time_order")),
    ]
