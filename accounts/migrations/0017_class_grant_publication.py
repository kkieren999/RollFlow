from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):
    dependencies = [("accounts", "0016_security_foundation")]
    operations = [
        migrations.AddField(model_name="staffaccessgrant", name="class_publication",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT,
                                    to="accounts.connectedschoolpublication")),
    ]
