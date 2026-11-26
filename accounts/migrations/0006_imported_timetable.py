from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):
    dependencies=[("accounts","0005_schoolperiod_active"),migrations.swappable_dependency(settings.AUTH_USER_MODEL)]
    operations=[
        migrations.CreateModel(name="ImportedTimetable",fields=[
            ("id",models.BigAutoField(auto_created=True,primary_key=True,serialize=False,verbose_name="ID")),
            ("name",models.CharField(max_length=100)),
            ("digest",models.CharField(max_length=64,unique=True)),
            ("status",models.CharField(max_length=12,choices=[("draft","Draft"),("published","Published"),("archived","Archived")],default="draft")),
            ("summary",models.JSONField(default=dict)),
            ("created_at",models.DateTimeField(auto_now_add=True)),
            ("published_at",models.DateTimeField(blank=True,null=True)),
            ("created_by",models.ForeignKey(null=True,on_delete=django.db.models.deletion.SET_NULL,to=settings.AUTH_USER_MODEL)),
        ],options={"ordering":["-created_at"],"constraints":[models.UniqueConstraint(fields=["status"],condition=models.Q(status="published"),name="single_published_import")]}),
        migrations.CreateModel(name="ImportedTimetableDay",fields=[
            ("id",models.BigAutoField(auto_created=True,primary_key=True,serialize=False,verbose_name="ID")),
            ("date",models.DateField()),
            ("allocations",models.JSONField(default=list)),
            ("version",models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,related_name="days",to="accounts.importedtimetable")),
        ],options={"ordering":["date"],"constraints":[models.UniqueConstraint(fields=["version","date"],name="unique_imported_day")]}),
    ]
