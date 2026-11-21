from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("accounts", "0006_imported_timetable")]

    operations = [
        # Existing links are deliberately unverified until school administration
        # confirms the staff identity against an authoritative source.
        migrations.AddField(
            model_name="staffprofile",
            name="timetable_link_verified",
            field=models.BooleanField(default=False),
        ),
    ]
