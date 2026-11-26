from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [("accounts", "0009_oneschool_class_membership")]

    operations = [
        migrations.CreateModel(
            name="OneSchoolLineAllocation",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("line_number", models.PositiveSmallIntegerField()),
                ("year_level", models.PositiveSmallIntegerField()),
                ("weekday", models.PositiveSmallIntegerField()),
                ("period", models.PositiveSmallIntegerField()),
                ("class_code", models.CharField(max_length=30)),
                ("staff_code", models.CharField(blank=True, max_length=40)),
                ("room_code", models.CharField(blank=True, max_length=40)),
                ("batch", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="line_allocations", to="accounts.oneschoolarchivebatch")),
            ],
            options={
                "constraints": [models.UniqueConstraint(fields=("batch", "weekday", "period", "class_code"), name="unique_oneschool_line_class_slot")],
            },
        ),
        migrations.CreateModel(
            name="OneSchoolStaffClassReference",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("staff_code", models.CharField(max_length=40)),
                ("class_code", models.CharField(max_length=30)),
                ("subject_name", models.CharField(blank=True, max_length=100)),
                ("line_number", models.PositiveSmallIntegerField(blank=True, null=True)),
                ("batch", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="staff_class_references", to="accounts.oneschoolarchivebatch")),
            ],
            options={
                "constraints": [models.UniqueConstraint(fields=("batch", "staff_code", "class_code"), name="unique_oneschool_staff_class_evidence")],
            },
        ),
    ]
