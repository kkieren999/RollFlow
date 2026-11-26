from django import forms
from django.core.exceptions import ValidationError
from .models import Student

class StudentForm(forms.ModelForm):
    class Meta:
        model = Student
        fields = ["student_id", "first_name", "last_name", "preferred_name", "year_level", "home_group", "status", "enrolled_on", "left_on"]
        widgets = {"enrolled_on": forms.DateInput(attrs={"type":"date"}, format="%Y-%m-%d"), "left_on": forms.DateInput(attrs={"type":"date"}, format="%Y-%m-%d")}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.fields["student_id"].disabled = True

    def clean_student_id(self):
        value = self.cleaned_data["student_id"].strip().upper()
        if not value or not all(c.isalnum() or c in "-_" for c in value):
            raise ValidationError("Use letters, numbers, hyphens or underscores.")
        if Student.objects.filter(student_id__iexact=value).exclude(pk=self.instance.pk).exists():
            raise ValidationError("Student ID already exists.")
        return value

    def clean(self):
        data = super().clean()
        if data.get("status") == Student.Status.LEFT and not data.get("left_on"):
            self.add_error("left_on", "Enter the leaving date.")
        if data.get("status") != Student.Status.LEFT and data.get("left_on"):
            self.add_error("left_on", "Only students who have left should have a leaving date.")
        if data.get("enrolled_on") and data.get("left_on") and data["left_on"] < data["enrolled_on"]:
            self.add_error("left_on", "Leaving date must not precede enrolment.")
        return data

class StudentPhotoForm(forms.Form):
    photo = forms.FileField(label="Fictional student portrait", widget=forms.ClearableFileInput(attrs={"accept":"image/jpeg,image/png"}))

class StudentImportForm(forms.Form):
    csv = forms.FileField(label="Student CSV file")
