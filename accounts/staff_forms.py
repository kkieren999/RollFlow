from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from .models import StaffProfile

ROLE_CHOICES = [("teacher", "Teacher (legacy default)"), ("staff", "Staff (no default teaching)"), ("admin", "Administrator")]

class StaffForm(forms.Form):
    staff_id = forms.CharField(label="Staff ID", max_length=40, required=False)
    verify_timetable_link = forms.BooleanField(
        required=False,
        label="I verified this OneSchool staff ID against the authorised staff record",
        help_text="Only tick after checking the person's identity. Unverified links cannot view published personal timetables in live mode.",
    )
    username = forms.CharField(max_length=150, validators=[User.username_validator])
    first_name = forms.CharField(max_length=100)
    last_name = forms.CharField(max_length=100)
    faculty = forms.CharField(max_length=100, required=False)
    campus = forms.CharField(max_length=100, required=False)
    role = forms.ChoiceField(choices=ROLE_CHOICES)
    teaching_permission = forms.ChoiceField(required=False, choices=[
        ("default", "Use legacy role default"), ("allow", "Allow assigned teaching"),
        ("deny", "No teaching access")], initial="default",
        help_text="Independent of account role. Teaching never grants system administration or another staff member's classes.")
    class_codes = forms.CharField(label="Draft class allocations", max_length=300, required=False,
        help_text="Planning only. Does not grant class access until the central class system exists.")
    active = forms.BooleanField(required=False, initial=True)
    password = forms.CharField(widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}), required=False, max_length=1024)
    password_confirm = forms.CharField(label="Confirm password", widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}), required=False, max_length=1024)

    def __init__(self, *args, target=None, actor=None, **kwargs):
        self.target, self.actor = target, actor
        if target:
            p = getattr(target, "staff_profile", None)
            kwargs.setdefault("initial", {
                "staff_id": p.staff_id if p else "", "faculty": p.faculty if p else "",
                "campus": p.campus if p else "", "class_codes": p.class_codes if p else "",
                "username": target.username, "first_name": target.first_name, "last_name": target.last_name,
                "role": "admin" if target.is_staff and target.is_superuser else "teacher" if target.groups.filter(name="Teacher").exists() else "staff",
                "teaching_permission": "allow" if p and p.teaching_enabled is True else "deny" if p and p.teaching_enabled is False else "default",
                "active": target.is_active,
            })
        super().__init__(*args, **kwargs)
        if target:
            self.fields.pop("password")
            self.fields.pop("password_confirm")
            self.fields["username"].disabled = True
            if actor and target.pk == actor.pk:
                self.fields["role"].disabled = True
                self.fields["active"].disabled = True
        else:
            self.fields["staff_id"].required = True
            self.fields["password"].required = True
            self.fields["password_confirm"].required = True

    def clean_username(self):
        value = self.cleaned_data["username"]
        if self.target:
            return self.target.username
        value = value.lower()
        if User.objects.filter(username__iexact=value).exists():
            raise ValidationError("This username already exists.")
        return value

    def clean_staff_id(self):
        value = self.cleaned_data["staff_id"].strip().upper()
        if value:
            existing = StaffProfile.objects.filter(staff_id__iexact=value)
            if self.target:
                existing = existing.exclude(user=self.target)
            if existing.exists():
                raise ValidationError("This staff ID already exists.")
        return value or None

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("verify_timetable_link") and not cleaned.get("staff_id"):
            self.add_error("verify_timetable_link", "Enter a staff ID before verifying its identity.")
        if self.target and self.actor and self.target.pk == self.actor.pk:
            cleaned["role"], cleaned["active"] = "admin", True
        if self.target and cleaned.get("active") and not self.target.has_usable_password():
            self.add_error("active", "Reset this account's password before activating it.")
        if not self.target and cleaned.get("password"):
            password = cleaned["password"]
            if password != cleaned.get("password_confirm"):
                self.add_error("password_confirm", "Passwords do not match.")
            candidate = User(username=cleaned.get("username", ""), first_name=cleaned.get("first_name", ""), last_name=cleaned.get("last_name", ""))
            try:
                validate_password(password, candidate)
            except ValidationError as err:
                self.add_error("password", err)
        return cleaned

class ResetPasswordForm(forms.Form):
    password = forms.CharField(label="New password", max_length=1024, widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}))
    password_confirm = forms.CharField(label="Confirm new password", max_length=1024, widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}))

    def __init__(self, *args, target, **kwargs):
        self.target = target
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("password") != cleaned.get("password_confirm"):
            self.add_error("password_confirm", "Passwords do not match.")
        if cleaned.get("password"):
            try:
                validate_password(cleaned["password"], self.target)
            except ValidationError as err:
                self.add_error("password", err)
        return cleaned

class StaffImportForm(forms.Form):
    csv = forms.FileField(label="CSV file")
