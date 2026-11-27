from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0017_class_grant_publication"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]
    operations = [
        migrations.CreateModel(name="AttendanceTransferReview", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("revision", models.PositiveIntegerField()),
            ("digest", models.CharField(max_length=64)),
            ("row_count", models.PositiveIntegerField()),
            ("reviewed_at", models.DateTimeField(auto_now_add=True)),
            ("reconciled_at", models.DateTimeField(blank=True, null=True)),
            ("roll", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="transfer_reviews", to="accounts.attendanceroll")),
            ("reviewed_by", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="+", to=settings.AUTH_USER_MODEL)),
            ("reconciled_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="+", to=settings.AUTH_USER_MODEL)),
        ]),
        migrations.AddConstraint(model_name="attendancetransferreview", constraint=models.UniqueConstraint(
            fields=("roll", "revision", "digest"), name="unique_attendance_transfer_review")),
    ]
