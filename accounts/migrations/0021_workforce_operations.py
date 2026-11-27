from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0020_student_movements"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]
    operations = [
        migrations.CreateModel(name="WorkforceEntry", fields=[
            ("id",models.BigAutoField(auto_created=True,primary_key=True,serialize=False,verbose_name="ID")),
            ("day",models.DateField()),
            ("kind",models.CharField(choices=[("absence","Full-day unavailability"),("duty","Supervision duty"),("room","Lesson room change"),("closure","School day exception (closed)")],max_length=12)),
            ("class_code",models.CharField(blank=True,max_length=30)),
            ("period",models.CharField(blank=True,max_length=50)),
            ("start",models.CharField(blank=True,max_length=5)),
            ("end",models.CharField(blank=True,max_length=5)),
            ("location",models.CharField(blank=True,max_length=100)),
            ("created_at",models.DateTimeField(auto_now_add=True)),
            ("cancelled_at",models.DateTimeField(blank=True,null=True)),
            ("staff",models.ForeignKey(blank=True,null=True,on_delete=django.db.models.deletion.PROTECT,related_name="+",to=settings.AUTH_USER_MODEL)),
            ("publication",models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,to="accounts.connectedschoolpublication")),
            ("created_by",models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,related_name="+",to=settings.AUTH_USER_MODEL)),
        ]),
        migrations.AddConstraint(model_name="workforceentry",constraint=models.UniqueConstraint(fields=("publication","day","staff"),condition=models.Q(kind="absence",cancelled_at__isnull=True),name="unique_workforce_absence")),
        migrations.AddConstraint(model_name="workforceentry",constraint=models.UniqueConstraint(fields=("publication","day","class_code","period","start"),condition=models.Q(kind="room",cancelled_at__isnull=True),name="unique_workforce_room")),
        migrations.AddConstraint(model_name="workforceentry",constraint=models.UniqueConstraint(fields=("publication","day"),condition=models.Q(kind="closure",cancelled_at__isnull=True),name="unique_workforce_closure")),
        migrations.AddIndex(model_name="workforceentry",index=models.Index(fields=["publication","day","kind"],name="workforce_pub_day_kind")),
        migrations.CreateModel(name="WorkforceNotice",fields=[
            ("id",models.BigAutoField(auto_created=True,primary_key=True,serialize=False,verbose_name="ID")),
            ("day",models.DateField()),
            ("message",models.CharField(max_length=240)),
            ("created_at",models.DateTimeField(auto_now_add=True)),
            ("acknowledged_at",models.DateTimeField(blank=True,null=True)),
            ("recipient",models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,related_name="+",to=settings.AUTH_USER_MODEL)),
            ("publication",models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,to="accounts.connectedschoolpublication")),
        ]),
    ]
