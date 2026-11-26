from datetime import time
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion

def seed_periods(apps, schema_editor):
    Period = apps.get_model("accounts", "SchoolPeriod")
    for code, label, start, end in [
        ("ROLL", "Home group", time(8,35), time(8,50)),
        ("1", "Period 1", time(9), time(10,10)),
        ("2", "Period 2", time(10,15), time(11,25)),
        ("3", "Period 3", time(11,30), time(12,40)),
        ("4", "Period 4", time(13,20), time(14,30)),
        ("5", "Period 5", time(14,35), time(15,10)),
    ]:
        Period.objects.get_or_create(code=code, defaults={"label":label,"start_time":start,"end_time":end})

class Migration(migrations.Migration):
    dependencies = [("accounts", "0003_student_studentphoto"), migrations.swappable_dependency(settings.AUTH_USER_MODEL)]
    operations = [
        migrations.CreateModel(name="SchoolClass", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("code", models.CharField(max_length=30, unique=True)),
            ("name", models.CharField(max_length=100)),
            ("subject", models.CharField(max_length=100)),
            ("year_level", models.PositiveSmallIntegerField(choices=[(i,f"Year {i}") for i in range(7,13)])),
            ("teacher", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="teaching_classes", to=settings.AUTH_USER_MODEL)),
            ("active", models.BooleanField(default=True)),
        ]),
        migrations.CreateModel(name="ClassEnrolment", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("school_class", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="enrolments", to="accounts.schoolclass")),
            ("student", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="class_enrolments", to="accounts.student")),
            ("start_date", models.DateField()),
            ("end_date", models.DateField(blank=True, null=True, help_text="Last enrolled day")),
        ], options={"constraints":[models.UniqueConstraint(fields=["school_class","student"], condition=models.Q(end_date__isnull=True), name="unique_open_class_enrolment"),models.CheckConstraint(condition=models.Q(end_date__isnull=True)|models.Q(end_date__gte=models.F("start_date")),name="class_enrolment_date_order")]}),
        migrations.CreateModel(name="Room", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("code", models.CharField(max_length=30,unique=True)),
            ("name", models.CharField(max_length=100,blank=True)),
            ("active", models.BooleanField(default=True)),
        ]),
        migrations.CreateModel(name="SchoolPeriod", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("code", models.CharField(max_length=20,unique=True)),
            ("label", models.CharField(max_length=50)),
            ("start_time", models.TimeField()),
            ("end_time", models.TimeField()),
        ], options={"ordering":["start_time"],"constraints":[models.CheckConstraint(condition=models.Q(end_time__gt=models.F("start_time")),name="school_period_time_order")]}),
        migrations.CreateModel(name="TimetableSlot", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("school_class", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="slots", to="accounts.schoolclass")),
            ("teacher", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="timetable_slots", to=settings.AUTH_USER_MODEL)),
            ("room", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="slots", to="accounts.room")),
            ("weekday", models.PositiveSmallIntegerField(choices=[(1,"Monday"),(2,"Tuesday"),(3,"Wednesday"),(4,"Thursday"),(5,"Friday")])),
            ("period", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="slots", to="accounts.schoolperiod")),
            ("active", models.BooleanField(default=True)),
        ], options={"ordering":["weekday","period__start_time","school_class__code"],"constraints":[
            models.UniqueConstraint(fields=["weekday","period","school_class"],condition=models.Q(active=True),name="unique_active_class_slot"),
            models.UniqueConstraint(fields=["weekday","period","teacher"],condition=models.Q(active=True),name="unique_active_teacher_slot"),
            models.UniqueConstraint(fields=["weekday","period","room"],condition=models.Q(active=True),name="unique_active_room_slot"),
        ]}),
        migrations.RunPython(seed_periods, migrations.RunPython.noop),
    ]
