from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion

def teacher_group(apps, schema_editor):
    apps.get_model("auth", "Group").objects.get_or_create(name="Teacher")

class Migration(migrations.Migration):
    initial = True
    dependencies = [migrations.swappable_dependency(settings.AUTH_USER_MODEL), ("auth", "0012_alter_user_first_name_max_length")]
    operations = [
        migrations.CreateModel(name="StaffProfile", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("staff_id", models.CharField(blank=True, max_length=40, null=True, unique=True)),
            ("faculty", models.CharField(blank=True, max_length=100)),
            ("campus", models.CharField(blank=True, max_length=100)),
            ("user", models.OneToOneField(on_delete=django.db.models.deletion.PROTECT, related_name="staff_profile", to=settings.AUTH_USER_MODEL)),
        ]),
        migrations.CreateModel(name="SecurityEvent", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("event", models.CharField(max_length=40)),
            ("created_at", models.DateTimeField(auto_now_add=True)),
            ("subject", models.CharField(blank=True, max_length=150)),
            ("actor", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
        ], options={"ordering": ["-created_at"]}),
        migrations.CreateModel(name="LoginWindow", fields=[
            ("key", models.CharField(max_length=64, primary_key=True, serialize=False)),
            ("count", models.PositiveIntegerField(default=0)),
            ("started_at", models.DateTimeField()),
        ]),
        migrations.RunPython(teacher_group, migrations.RunPython.noop),
    ]
