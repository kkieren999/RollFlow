from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0013_staffprofile_teaching_enabled"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]
    operations = [
        migrations.CreateModel(
            name="StaffAccessGrant",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("role", models.CharField(max_length=80)),
                ("scope", models.CharField(max_length=12)),
                ("scope_value", models.CharField(blank=True, max_length=100)),
                ("capabilities", models.JSONField(default=list)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,
                    related_name="school_access_grants", to=settings.AUTH_USER_MODEL)),
                ("granted_by", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,
                    related_name="+", to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
