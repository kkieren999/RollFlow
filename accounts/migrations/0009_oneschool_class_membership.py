from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [("accounts", "0008_oneschool_import_archive")]

    operations = [
        migrations.AlterField(
            model_name="oneschoolarchivebatch",
            name="kind",
            field=models.CharField(max_length=20, choices=[
                ("students", "SM110 Student List (Excel)"),
                ("staff_pdf", "Whole-staff Timetable (PDF)"),
                ("tt_alignment", "TTLineAlignmentExport (multiple files)"),
                ("class_members", "ExportStudentClass (CSV)"),
            ]),
        ),
        migrations.AlterField(
            model_name="oneschoolarchivebatch",
            name="status",
            field=models.CharField(max_length=12, default="staged", choices=[
                ("staged", "Awaiting review"),
                ("applied", "Applied after administrator review"),
            ]),
        ),
        migrations.CreateModel(
            name="OneSchoolClassMembership",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("class_code", models.CharField(max_length=30)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("source_batch", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="class_memberships", to="accounts.oneschoolarchivebatch")),
                ("student", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="oneschool_memberships", to="accounts.student")),
            ],
            options={
                "ordering": ["class_code", "student__last_name", "student__first_name"],
                "constraints": [models.UniqueConstraint(fields=["student", "class_code"], name="unique_oneschool_student_class")],
            },
        ),
    ]
