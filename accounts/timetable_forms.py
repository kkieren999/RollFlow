from django import forms
from django.contrib.auth.models import User
from django.db.models import Q
from .models import SchoolClass, ClassEnrolment, Student, Room, SchoolPeriod, TimetableSlot

def teachers():
    return User.objects.filter(is_active=True,is_staff=False,is_superuser=False,groups__name="Teacher").order_by("last_name","first_name","username").distinct()

def normalize_code(value):
    value = value.strip().upper()
    if not value or not all(c.isalnum() or c in "-_" for c in value):
        raise forms.ValidationError("Use letters, numbers, hyphens or underscores.")
    return value

class ClassForm(forms.ModelForm):
    class Meta:
        model = SchoolClass
        fields = ["code","name","subject","year_level","teacher","active"]
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.fields["teacher"].queryset = teachers()
        if self.instance.pk:
            self.fields["code"].disabled = True
            # Existing scheduled slots retain their explicit teacher assignment.
            current = self.instance.teacher_id
            self.fields["teacher"].queryset = User.objects.filter(Q(pk=current)|Q(pk__in=teachers().values("pk")))
    def clean_code(self):
        return normalize_code(self.cleaned_data["code"])

class EnrolmentForm(forms.ModelForm):
    class Meta:
        model = ClassEnrolment
        fields = ["student","start_date"]
        widgets = {"start_date": forms.DateInput(attrs={"type":"date"},format="%Y-%m-%d")}
    def __init__(self,*args,school_class,**kwargs):
        super().__init__(*args,**kwargs)
        self.school_class = school_class
        self.fields["student"].queryset = Student.objects.filter(status=Student.Status.ACTIVE,year_level=school_class.year_level).order_by("last_name","first_name")
    def clean(self):
        c = super().clean()
        if c.get("student") and c.get("start_date"):
            if not self.school_class.active:
                raise forms.ValidationError("Class is inactive.")
            student = c["student"]
            start = c["start_date"]
            if student.enrolled_on and start < student.enrolled_on:
                raise forms.ValidationError("Class enrolment cannot precede school enrolment.")
            if ClassEnrolment.objects.filter(school_class=self.school_class,student=student).filter(Q(end_date__isnull=True)|Q(end_date__gte=start)).exists():
                raise forms.ValidationError("An overlapping class enrolment already exists.")
        return c

class EndEnrolmentForm(forms.Form):
    end_date = forms.DateField(label="Last enrolled day",widget=forms.DateInput(attrs={"type":"date"},format="%Y-%m-%d"))

class RoomForm(forms.ModelForm):
    class Meta:
        model = Room
        fields = ["code","name","active"]
    def clean_code(self):
        return normalize_code(self.cleaned_data["code"])

class PeriodForm(forms.ModelForm):
    class Meta:
        model = SchoolPeriod
        fields = ["code","label","start_time","end_time"]
        widgets = {"start_time":forms.TimeInput(attrs={"type":"time"},format="%H:%M"),"end_time":forms.TimeInput(attrs={"type":"time"},format="%H:%M")}
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        if self.instance.pk:
            self.fields["code"].disabled = True
    def clean_code(self):
        return normalize_code(self.cleaned_data["code"])
    def clean(self):
        c = super().clean()
        start,end = c.get("start_time"),c.get("end_time")
        if start and end:
            if end <= start:
                raise forms.ValidationError("End time must be after start time.")
            if self.instance.active and SchoolPeriod.objects.exclude(pk=self.instance.pk).filter(active=True,start_time__lt=end,end_time__gt=start).exists():
                raise forms.ValidationError("Periods must not overlap.")
        return c

class SlotForm(forms.ModelForm):
    class Meta:
        model = TimetableSlot
        fields = ["school_class","teacher","room","weekday","period","active"]
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.fields["teacher"].queryset = teachers()
        self.fields["school_class"].queryset = SchoolClass.objects.filter(active=True).order_by("code")
        self.fields["room"].queryset = Room.objects.filter(active=True).order_by("code")
        self.fields["period"].queryset = SchoolPeriod.objects.filter(active=True)
    def clean(self):
        c = super().clean()
        if c.get("active") and all(c.get(k) for k in ("school_class","teacher","room","weekday","period")):
            matches = TimetableSlot.objects.filter(active=True,weekday=c["weekday"],period=c["period"]).exclude(pk=self.instance.pk)
            for key in ("school_class","teacher","room"):
                if matches.filter(**{key:c[key]}).exists():
                    self.add_error(key,"Already scheduled in this period.")
        return c

class TimetableImportForm(forms.Form):
    csv = forms.FileField(label="Timetable CSV")
