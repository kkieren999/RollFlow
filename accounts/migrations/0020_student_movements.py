from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0019_attendance_operations"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]
    operations = [
        migrations.CreateModel(name="MovementDestination", fields=[
            ("id",models.BigAutoField(auto_created=True,primary_key=True,serialize=False,verbose_name="ID")),
            ("name",models.CharField(max_length=80,unique=True)),
            ("expected_minutes",models.PositiveSmallIntegerField(default=10)),
            ("requires_reception",models.BooleanField(default=False)),
            ("active",models.BooleanField(default=True)),
            ("created_at",models.DateTimeField(auto_now_add=True)),
            ("created_by",models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,to=settings.AUTH_USER_MODEL)),
        ]),
        migrations.AddConstraint(model_name="movementdestination",constraint=models.CheckConstraint(
            condition=models.Q(expected_minutes__gte=1,expected_minutes__lte=180),name="movement_duration_bounds")),
        migrations.CreateModel(name="StudentMovement",fields=[
            ("id",models.BigAutoField(auto_created=True,primary_key=True,serialize=False,verbose_name="ID")),
            ("destination_name",models.CharField(max_length=80)),
            ("requires_reception",models.BooleanField()),
            ("lesson_date",models.DateField()),
            ("class_code",models.CharField(max_length=30)),
            ("period",models.CharField(max_length=50)),
            ("start",models.CharField(max_length=5)),
            ("end",models.CharField(max_length=5)),
            ("origin_room",models.CharField(blank=True,max_length=100)),
            ("state",models.CharField(choices=[("outbound","Departed classroom"),("arrived","Checked in"),("returning","Returning to classroom"),("returned","Returned"),("closed","Administratively closed — return unconfirmed")],default="outbound",max_length=12)),
            ("revision",models.PositiveIntegerField(default=1)),
            ("departed_at",models.DateTimeField()),
            ("due_at",models.DateTimeField()),
            ("closed_at",models.DateTimeField(blank=True,null=True)),
            ("publication",models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,to="accounts.connectedschoolpublication")),
            ("student",models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,to="accounts.student")),
            ("issuer",models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,to=settings.AUTH_USER_MODEL)),
            ("destination",models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,to="accounts.movementdestination")),
        ]),
        migrations.AddConstraint(model_name="studentmovement",constraint=models.UniqueConstraint(
            fields=("student",),condition=models.Q(closed_at__isnull=True),name="one_open_student_movement")),
        migrations.AddConstraint(model_name="studentmovement",constraint=models.CheckConstraint(
            condition=models.Q(state__in=["outbound","arrived","returning"],closed_at__isnull=True) | models.Q(state__in=["returned","closed"],closed_at__isnull=False),name="movement_closed_state")),
        migrations.AddConstraint(model_name="studentmovement",constraint=models.CheckConstraint(
            condition=models.Q(due_at__gt=models.F("departed_at")),name="movement_due_order")),
        migrations.AddIndex(model_name="studentmovement",index=models.Index(fields=["closed_at","due_at"],name="movement_open_due_idx")),
        migrations.CreateModel(name="MovementEvent",fields=[
            ("id",models.BigAutoField(auto_created=True,primary_key=True,serialize=False,verbose_name="ID")),
            ("revision",models.PositiveIntegerField()),
            ("action",models.CharField(max_length=20)),
            ("from_state",models.CharField(blank=True,max_length=12)),
            ("to_state",models.CharField(max_length=12)),
            ("reason_code",models.CharField(blank=True,max_length=30)),
            ("created_at",models.DateTimeField(auto_now_add=True)),
            ("movement",models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,related_name="events",to="accounts.studentmovement")),
            ("actor",models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,to=settings.AUTH_USER_MODEL)),
        ]),
        migrations.AddConstraint(model_name="movementevent",constraint=models.UniqueConstraint(
            fields=("movement","revision"),name="unique_movement_revision")),
    ]
