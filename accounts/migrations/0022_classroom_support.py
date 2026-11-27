from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):
    dependencies = [("accounts","0021_workforce_operations"), migrations.swappable_dependency(settings.AUTH_USER_MODEL)]
    operations = [
        migrations.CreateModel(name="ClassroomPlan",fields=[
            ("id",models.BigAutoField(auto_created=True,primary_key=True,serialize=False,verbose_name="ID")),
            ("class_code",models.CharField(max_length=30)),("seats",models.JSONField(default=dict)),
            ("revision",models.PositiveIntegerField(default=1)),("updated_at",models.DateTimeField(auto_now=True)),
            ("publication",models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,to="accounts.connectedschoolpublication")),
            ("teacher",models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,to=settings.AUTH_USER_MODEL)),
        ]),
        migrations.AddConstraint(model_name="classroomplan",constraint=models.UniqueConstraint(fields=("publication","teacher","class_code"),name="unique_classroom_plan")),
        migrations.CreateModel(name="ClassroomObservation",fields=[
            ("id",models.BigAutoField(auto_created=True,primary_key=True,serialize=False,verbose_name="ID")),
            ("class_code",models.CharField(max_length=30)),("lesson_date",models.DateField()),("category",models.CharField(max_length=30)),
            ("created_at",models.DateTimeField(auto_now_add=True)),("withdrawn_at",models.DateTimeField(blank=True,null=True)),
            ("publication",models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,to="accounts.connectedschoolpublication")),
            ("teacher",models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,to=settings.AUTH_USER_MODEL)),
            ("student",models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,to="accounts.student")),
        ]),
        migrations.CreateModel(name="SupportTask",fields=[
            ("id",models.BigAutoField(auto_created=True,primary_key=True,serialize=False,verbose_name="ID")),
            ("class_code",models.CharField(max_length=30)),("category",models.CharField(max_length=30)),
            ("due_on",models.DateField()),("state",models.CharField(default="pending",max_length=12)),
            ("revision",models.PositiveIntegerField(default=1)),("created_at",models.DateTimeField(auto_now_add=True)),
            ("closed_at",models.DateTimeField(blank=True,null=True)),
            ("publication",models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,to="accounts.connectedschoolpublication")),
            ("student",models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,to="accounts.student")),
            ("requested_by",models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,related_name="+",to=settings.AUTH_USER_MODEL)),
            ("assigned_to",models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,related_name="+",to=settings.AUTH_USER_MODEL)),
        ]),
        migrations.AddConstraint(model_name="supporttask",constraint=models.CheckConstraint(condition=models.Q(state__in=["pending","accepted"],closed_at__isnull=True)|models.Q(state__in=["completed","cancelled"],closed_at__isnull=False),name="support_task_state")),
        migrations.CreateModel(name="SupportReferral",fields=[
            ("id",models.BigAutoField(auto_created=True,primary_key=True,serialize=False,verbose_name="ID")),
            ("class_code",models.CharField(max_length=30)),("category",models.CharField(max_length=30)),
            ("state",models.CharField(default="pending",max_length=12)),("revision",models.PositiveIntegerField(default=1)),
            ("follow_up_on",models.DateField()),("created_at",models.DateTimeField(auto_now_add=True)),
            ("closed_at",models.DateTimeField(blank=True,null=True)),
            ("publication",models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,to="accounts.connectedschoolpublication")),
            ("student",models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,to="accounts.student")),
            ("requested_by",models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,related_name="+",to=settings.AUTH_USER_MODEL)),
            ("assigned_to",models.ForeignKey(blank=True,null=True,on_delete=django.db.models.deletion.PROTECT,related_name="+",to=settings.AUTH_USER_MODEL)),
        ]),
        migrations.AddConstraint(model_name="supportreferral",constraint=models.CheckConstraint(condition=models.Q(state__in=["pending","assigned","reviewed"],closed_at__isnull=True)|models.Q(state__in=["closed","withdrawn"],closed_at__isnull=False),name="support_referral_state")),
    ]
