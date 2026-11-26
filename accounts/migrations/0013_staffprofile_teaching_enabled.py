from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [("accounts", "0012_pending_teacher_setup")]
    operations = [
        migrations.AddField(
            model_name="staffprofile",
            name="teaching_enabled",
            field=models.BooleanField(blank=True, default=None, null=True),
        ),
    ]
