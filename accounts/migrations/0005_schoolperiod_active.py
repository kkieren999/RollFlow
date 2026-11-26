from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [("accounts", "0004_timetable")]
    operations = [migrations.AddField(model_name="schoolperiod", name="active", field=models.BooleanField(default=True))]
