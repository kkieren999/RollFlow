from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):
    dependencies = [("accounts", "0002_staffprofile_class_codes")]
    operations = [
        migrations.CreateModel(name="Student", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("student_id", models.CharField(max_length=40, unique=True)),
            ("first_name", models.CharField(max_length=100)),
            ("last_name", models.CharField(max_length=100)),
            ("preferred_name", models.CharField(blank=True, max_length=100)),
            ("year_level", models.PositiveSmallIntegerField(choices=[(7,"Year 7"),(8,"Year 8"),(9,"Year 9"),(10,"Year 10"),(11,"Year 11"),(12,"Year 12")])),
            ("home_group", models.CharField(blank=True, max_length=30)),
            ("status", models.CharField(choices=[("active","Enrolled"),("inactive","Inactive"),("left","Left school")], default="active", max_length=12)),
            ("enrolled_on", models.DateField(blank=True, null=True)),
            ("left_on", models.DateField(blank=True, null=True)),
            ("created_at", models.DateTimeField(auto_now_add=True)),
            ("updated_at", models.DateTimeField(auto_now=True)),
        ]),
        migrations.CreateModel(name="StudentPhoto", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("image", models.BinaryField()),
            ("updated_at", models.DateTimeField(auto_now=True)),
            ("student", models.OneToOneField(on_delete=django.db.models.deletion.PROTECT, related_name="portrait", to="accounts.student")),
        ]),
    ]
