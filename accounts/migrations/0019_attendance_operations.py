from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0018_transfer_review"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]
    operations = [
        migrations.AddField(model_name="attendancerevision",name="reason",field=models.CharField(blank=True,max_length=500)),
        migrations.CreateModel(name="ReliefAttendanceAssignment",fields=[
            ("id",models.BigAutoField(auto_created=True,primary_key=True,serialize=False,verbose_name="ID")),
            ("lesson_date",models.DateField()),
            ("class_code",models.CharField(max_length=30)),
            ("period",models.CharField(max_length=50)),
            ("start",models.CharField(max_length=5)),
            ("end",models.CharField(max_length=5)),
            ("created_at",models.DateTimeField(auto_now_add=True)),
            ("expires_at",models.DateTimeField()),
            ("cancelled_at",models.DateTimeField(blank=True,null=True)),
            ("publication",models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,to="accounts.connectedschoolpublication")),
            ("regular_teacher",models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,related_name="+",to=settings.AUTH_USER_MODEL)),
            ("relief_teacher",models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,related_name="+",to=settings.AUTH_USER_MODEL)),
            ("created_by",models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,related_name="+",to=settings.AUTH_USER_MODEL)),
        ]),
        migrations.AddConstraint(model_name="reliefattendanceassignment",constraint=models.UniqueConstraint(
            fields=("publication","lesson_date","class_code","period","start"),
            condition=models.Q(cancelled_at__isnull=True),name="unique_active_relief_attendance")),
    ]
