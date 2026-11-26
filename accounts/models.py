from django.conf import settings
from django.db import models

class StaffProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="staff_profile")
    staff_id = models.CharField(max_length=40, blank=True, unique=True, null=True)
    # Only an administrator's explicit identity verification grants live timetable access.
    timetable_link_verified = models.BooleanField(default=False)
    # None preserves the legacy Teacher group default; explicit decisions take precedence.
    teaching_enabled = models.BooleanField(null=True, blank=True, default=None)
    faculty = models.CharField(max_length=100, blank=True)
    campus = models.CharField(max_length=100, blank=True)
    class_codes = models.CharField(max_length=300, blank=True)
    def __str__(self):
        return self.user.get_username()

class SecurityEvent(models.Model):
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    event = models.CharField(max_length=40)
    created_at = models.DateTimeField(auto_now_add=True)
    subject = models.CharField(max_length=150, blank=True)
    class Meta:
        ordering = ["-created_at"]

class LoginWindow(models.Model):
    # HMAC-derived key; do not log passwords or retain the raw IP.
    key = models.CharField(max_length=64, primary_key=True)
    count = models.PositiveIntegerField(default=0)
    started_at = models.DateTimeField()

class Student(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "active", "Enrolled"
        INACTIVE = "inactive", "Inactive"
        LEFT = "left", "Left school"
    student_id = models.CharField(max_length=40, unique=True)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    preferred_name = models.CharField(max_length=100, blank=True)
    year_level = models.PositiveSmallIntegerField(choices=[(i, f"Year {i}") for i in range(7, 13)])
    home_group = models.CharField(max_length=30, blank=True)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.ACTIVE)
    enrolled_on = models.DateField(blank=True, null=True)
    left_on = models.DateField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    def __str__(self):
        return self.student_id

class StudentPhoto(models.Model):
    student = models.OneToOneField(Student, on_delete=models.PROTECT, related_name="portrait")
    image = models.BinaryField()
    updated_at = models.DateTimeField(auto_now=True)

class SchoolClass(models.Model):
    code = models.CharField(max_length=30, unique=True)
    name = models.CharField(max_length=100)
    subject = models.CharField(max_length=100)
    year_level = models.PositiveSmallIntegerField(choices=[(i, f"Year {i}") for i in range(7, 13)])
    teacher = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="teaching_classes")
    active = models.BooleanField(default=True)
    def __str__(self):
        return f"{self.code} — {self.name}"

class ClassEnrolment(models.Model):
    school_class = models.ForeignKey(SchoolClass, on_delete=models.PROTECT, related_name="enrolments")
    student = models.ForeignKey(Student, on_delete=models.PROTECT, related_name="class_enrolments")
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True, help_text="Last enrolled day")
    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["school_class", "student"], condition=models.Q(end_date__isnull=True), name="unique_open_class_enrolment"),
            models.CheckConstraint(condition=models.Q(end_date__isnull=True) | models.Q(end_date__gte=models.F("start_date")), name="class_enrolment_date_order"),
        ]

class Room(models.Model):
    code = models.CharField(max_length=30, unique=True)
    name = models.CharField(max_length=100, blank=True)
    active = models.BooleanField(default=True)
    def __str__(self):
        return self.code

class SchoolPeriod(models.Model):
    code = models.CharField(max_length=20, unique=True)
    label = models.CharField(max_length=50)
    start_time = models.TimeField()
    end_time = models.TimeField()
    active = models.BooleanField(default=True)
    class Meta:
        ordering = ["start_time"]
        constraints = [models.CheckConstraint(condition=models.Q(end_time__gt=models.F("start_time")), name="school_period_time_order")]
    def __str__(self):
        return self.label

class TimetableSlot(models.Model):
    school_class = models.ForeignKey(SchoolClass, on_delete=models.PROTECT, related_name="slots")
    teacher = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="timetable_slots")
    room = models.ForeignKey(Room, on_delete=models.PROTECT, related_name="slots")
    weekday = models.PositiveSmallIntegerField(choices=[(1,"Monday"),(2,"Tuesday"),(3,"Wednesday"),(4,"Thursday"),(5,"Friday")])
    period = models.ForeignKey(SchoolPeriod, on_delete=models.PROTECT, related_name="slots")
    active = models.BooleanField(default=True)
    class Meta:
        ordering = ["weekday", "period__start_time", "school_class__code"]
        constraints = [
            models.UniqueConstraint(fields=["weekday","period","school_class"], condition=models.Q(active=True), name="unique_active_class_slot"),
            models.UniqueConstraint(fields=["weekday","period","teacher"], condition=models.Q(active=True), name="unique_active_teacher_slot"),
            models.UniqueConstraint(fields=["weekday","period","room"], condition=models.Q(active=True), name="unique_active_room_slot"),
        ]

class ImportedTimetable(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        PUBLISHED = "published", "Published"
        ARCHIVED = "archived", "Archived"
    name = models.CharField(max_length=100)
    digest = models.CharField(max_length=64, unique=True)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.DRAFT)
    summary = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    published_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL)
    class Meta:
        ordering = ["-created_at"]
        constraints = [models.UniqueConstraint(fields=["status"],condition=models.Q(status="published"),name="single_published_import")]

class ImportedTimetableDay(models.Model):
    version = models.ForeignKey(ImportedTimetable,on_delete=models.PROTECT,related_name="days")
    date = models.DateField()
    allocations = models.JSONField(default=list)
    class Meta:
        ordering = ["date"]
        constraints = [models.UniqueConstraint(fields=["version","date"],name="unique_imported_day")]


class OneSchoolArchiveBatch(models.Model):
    """A versioned, administrator-only record of an offline OneSchool upload."""
    class Kind(models.TextChoices):
        STUDENTS = "students", "SM110 Student List (Excel)"
        STAFF_PDF = "staff_pdf", "Whole-staff Timetable (PDF)"
        TT_ALIGNMENT = "tt_alignment", "TTLineAlignmentExport (multiple files)"
        CLASS_MEMBERS = "class_members", "ExportStudentClass (CSV)"

    class Status(models.TextChoices):
        STAGED = "staged", "Awaiting review"
        APPLIED = "applied", "Applied after administrator review"

    kind = models.CharField(max_length=20, choices=Kind.choices)
    label = models.CharField(max_length=120)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.STAGED)
    applied_at = models.DateTimeField(null=True, blank=True)
    source_purged_at = models.DateTimeField(null=True, blank=True)
    summary = models.JSONField(default=dict)
    class Meta:
        ordering = ["-created_at"]


class OneSchoolArchivedFile(models.Model):
    """Metadata only; actual export bytes are encrypted on the instance disk."""
    batch = models.ForeignKey(OneSchoolArchiveBatch, on_delete=models.PROTECT, related_name="files")
    original_name = models.CharField(max_length=180)
    storage_token = models.CharField(max_length=32, unique=True)
    sha256 = models.CharField(max_length=64)
    size = models.PositiveIntegerField()
    format = models.CharField(max_length=12)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        ordering = ["id"]
        constraints = [
            models.UniqueConstraint(fields=["batch", "sha256"], name="unique_file_digest_in_import_batch"),
        ]


class OneSchoolClassMembership(models.Model):
    """Reviewed OneSchool EQID-to-class-code link (not a teacher assignment).

    SchoolClass requires a manually verified teacher; published timetable
    classes can be present without a SchoolClass row. Using class_code
    independently avoids inventing a staff account or teacher identity.
    """
    student = models.ForeignKey(Student, on_delete=models.PROTECT, related_name="oneschool_memberships")
    class_code = models.CharField(max_length=30)
    source_batch = models.ForeignKey(OneSchoolArchiveBatch, on_delete=models.PROTECT,
                                     related_name="class_memberships")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["class_code", "student__last_name", "student__first_name"]
        constraints = [
            models.UniqueConstraint(fields=["student", "class_code"], name="unique_oneschool_student_class"),
        ]


class OneSchoolLineAllocation(models.Model):
    """Reviewed line-alignment row; a staff code is *not* a verified login ID."""
    batch = models.ForeignKey(OneSchoolArchiveBatch, on_delete=models.PROTECT, related_name="line_allocations")
    line_number = models.PositiveSmallIntegerField()
    year_level = models.PositiveSmallIntegerField()
    weekday = models.PositiveSmallIntegerField()
    period = models.PositiveSmallIntegerField()
    class_code = models.CharField(max_length=30)
    staff_code = models.CharField(max_length=40, blank=True)
    room_code = models.CharField(max_length=40, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["batch", "weekday", "period", "class_code"],
                                    name="unique_oneschool_line_class_slot"),
        ]


class OneSchoolStaffClassReference(models.Model):
    """PDF legend evidence, never automatic permission or staff-ID mapping."""
    batch = models.ForeignKey(OneSchoolArchiveBatch, on_delete=models.PROTECT, related_name="staff_class_references")
    staff_code = models.CharField(max_length=40)
    class_code = models.CharField(max_length=30)
    subject_name = models.CharField(max_length=100, blank=True)
    line_number = models.PositiveSmallIntegerField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["batch", "staff_code", "class_code"],
                                    name="unique_oneschool_staff_class_evidence"),
        ]


class ConnectedStaffMapping(models.Model):
    """Explicit administrator attestation connecting a printed code to a verified account."""
    staff_code = models.CharField(max_length=40, unique=True)
    profile = models.OneToOneField(StaffProfile, on_delete=models.PROTECT, related_name="connected_mapping")
    verified_staff_id = models.CharField(max_length=40)
    verified_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    verified_at = models.DateTimeField(auto_now=True)


class ConnectedSchoolPublication(models.Model):
    """Immutable reviewed projection of one term's approved sources."""
    name = models.CharField(max_length=100)
    starts = models.DateField()
    ends = models.DateField()
    active = models.BooleanField(default=True)
    source_batches = models.JSONField(default=dict)
    snapshot = models.JSONField(default=dict)
    digest = models.CharField(max_length=64)
    published_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    published_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-published_at", "-pk"]
        constraints = [
            models.UniqueConstraint(fields=["active"], condition=models.Q(active=True),
                                    name="single_active_connected_school"),
            models.CheckConstraint(condition=models.Q(ends__gte=models.F("starts")),
                                   name="connected_school_date_order"),
        ]


class PendingTeacherSetup(models.Model):
    """Imported staff candidate, not a verified identity."""
    staff_code = models.CharField(max_length=40, unique=True)
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="pending_teacher_setup")
    source_batch = models.ForeignKey(OneSchoolArchiveBatch, on_delete=models.PROTECT)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)
    activated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+", null=True, blank=True)
    activated_at = models.DateTimeField(null=True, blank=True)


class StaffAccessGrant(models.Model):
    """Explicit, bounded read access. Never confers Django admin or teaching."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                             related_name="school_access_grants")
    role = models.CharField(max_length=80)
    scope = models.CharField(max_length=12)
    scope_value = models.CharField(max_length=100, blank=True)
    capabilities = models.JSONField(default=list)
    created_at = models.DateTimeField(auto_now_add=True)
    granted_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
                                   related_name="+")
