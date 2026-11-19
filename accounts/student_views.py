"""Administrator-only fictional student development workflows."""
import csv
import io
from datetime import date
from PIL import Image, ImageOps, UnidentifiedImageError
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.http import HttpResponse, HttpResponseBadRequest, Http404
from django.shortcuts import get_object_or_404, redirect
from django.views.decorators.http import require_http_methods, require_POST
from .models import Student, StudentPhoto, SecurityEvent
from .staff_views import administrator, page
from .student_forms import StudentForm, StudentPhotoForm, StudentImportForm

def student_log(request, event, student):
    SecurityEvent.objects.create(actor=request.user, event=event, subject=student.student_id)

@administrator
@require_http_methods(["GET"])
def directory(request):
    q = request.GET.get("q", "").strip()[:150]
    year = request.GET.get("year", "")
    group = request.GET.get("group", "").strip()[:30]
    status = request.GET.get("status", "all")
    students = Student.objects.all().order_by("last_name", "first_name", "student_id")
    if q:
        students = students.filter(Q(student_id__icontains=q) | Q(first_name__icontains=q) | Q(last_name__icontains=q) | Q(preferred_name__icontains=q))
    if year in [str(x) for x in range(7, 13)]:
        students = students.filter(year_level=int(year))
    if group:
        students = students.filter(home_group__iexact=group)
    if status in Student.Status.values:
        students = students.filter(status=status)
    sort=request.GET.get("sort","name")
    orders={"name":("last_name","first_name"),"id":("student_id",),"year":("year_level","home_group"),"status":("status",)}
    sort=sort if sort in orders else "name"
    direction="desc" if request.GET.get("dir")=="desc" else "asc"
    students=students.order_by(*[("-" if direction=="desc" else "")+f for f in orders[sort]],"pk")
    return page(request, "students", student_page=Paginator(students, 50).get_page(request.GET.get("page")), q=q, year=year, group=group, status=status, sort=sort, direction=direction,
        years=range(7, 13), statuses=Student.Status.choices, home_groups=Student.objects.exclude(home_group="").order_by("home_group").values_list("home_group", flat=True).distinct())

@administrator
@require_http_methods(["GET"])
def detail(request, pk):
    student = get_object_or_404(Student, pk=pk)
    return page(request, "students", student=student, student_detail=True, photo_form=StudentPhotoForm(), events=SecurityEvent.objects.filter(subject=student.student_id, event__startswith="student_").select_related("actor")[:30])

@administrator
@require_http_methods(["GET", "POST"])
def edit(request, pk=None):
    student = get_object_or_404(Student, pk=pk) if pk is not None else None
    form = StudentForm(request.POST if request.method == "POST" else None, instance=student)
    if request.method == "POST" and form.is_valid():
        try:
            with transaction.atomic():
                record = form.save()
                student_log(request, "student_updated" if student else "student_created", record)
            messages.success(request, "Student details saved.")
            return redirect("management-student-detail", pk=record.pk)
        except IntegrityError:
            form.add_error("student_id", "This student ID is already in use.")
    return page(request, "students", student_editor=True, student=student, student_form=form)

def clean_photo(upload):
    if upload.size > 5 * 1024 * 1024:
        raise ValidationError("Choose a JPEG or PNG below 5 MB.")
    try:
        with Image.open(upload) as image:
            if image.format not in ("JPEG", "PNG") or image.width * image.height > 16_000_000:
                raise ValidationError("Use a JPEG or PNG no larger than 16 megapixels.")
            image = ImageOps.exif_transpose(image).convert("RGB")
            image.thumbnail((480, 640), Image.Resampling.LANCZOS)
            output = io.BytesIO()
            image.save(output, format="JPEG", quality=83, optimize=True)
            return output.getvalue()
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError) as error:
        raise ValidationError("That image could not be read safely.") from error

@administrator
@require_POST
def photo_upload(request, pk):
    student = get_object_or_404(Student, pk=pk)
    form = StudentPhotoForm(request.POST, request.FILES)
    if form.is_valid():
        try:
            data = clean_photo(form.cleaned_data["photo"])
            with transaction.atomic():
                StudentPhoto.objects.update_or_create(student=student, defaults={"image": data})
                student_log(request, "student_photo_updated", student)
            messages.success(request, "Fictional portrait saved.")
            return redirect("management-student-detail", pk=pk)
        except ValidationError as err:
            form.add_error("photo", err)
    return page(request, "students", student=student, student_detail=True, photo_form=form, events=SecurityEvent.objects.filter(subject=student.student_id, event__startswith="student_").select_related("actor")[:30])

@administrator
@require_http_methods(["GET"])
def photo(request, pk):
    record = get_object_or_404(StudentPhoto, student_id=pk)
    response = HttpResponse(bytes(record.image), content_type="image/jpeg")
    response["Cache-Control"] = "private, no-store"
    response["Content-Disposition"] = 'inline; filename="student.jpg"'
    return response

@administrator
@require_POST
def photo_remove(request, pk):
    student = get_object_or_404(Student, pk=pk)
    with transaction.atomic():
        StudentPhoto.objects.filter(student=student).delete()
        student_log(request, "student_photo_removed", student)
    messages.success(request, "Portrait removed.")
    return redirect("management-student-detail", pk=pk)

CSV_HEADER = ["student_id", "first_name", "last_name", "preferred_name", "year_level", "home_group", "status", "enrolled_on", "left_on"]

def parse_student_csv(upload):
    if upload.size > 250_000:
        raise ValidationError("Choose a CSV below 250 KB.")
    try:
        reader = csv.DictReader(io.StringIO(upload.read().decode("utf-8-sig")), strict=True)
        if reader.fieldnames != CSV_HEADER:
            raise ValidationError("Use the exact nine-column header.")
        rows, seen = [], set()
        for line, row in enumerate(reader, 2):
            if line > 501:
                raise ValidationError("Import no more than 500 rows at once.")
            if None in row or any(value is None for value in row.values()):
                raise ValidationError(f"Invalid columns on row {line}.")
            data = {k:v.strip() for k,v in row.items()}
            form = StudentForm(data)
            if not form.is_valid():
                fields = ", ".join(form.errors.keys())
                raise ValidationError(f"Invalid student record on row {line}: {fields}.")
            student = form.save(commit=False)
            if student.student_id in seen:
                raise ValidationError(f"Duplicate student ID on row {line}.")
            seen.add(student.student_id)
            rows.append(student)
        if not rows:
            raise ValidationError("No student records were found.")
        return rows
    except (UnicodeError, csv.Error) as error:
        raise ValidationError("Use a valid UTF-8 CSV file.") from error

@administrator
@require_http_methods(["GET", "POST"])
def import_students(request):
    form = StudentImportForm(request.POST if request.method == "POST" else None, request.FILES if request.method == "POST" else None)
    if request.method == "POST" and form.is_valid():
        try:
            with transaction.atomic():
                records = parse_student_csv(form.cleaned_data["csv"])
                for record in records:
                    record.save(force_insert=True)
                    student_log(request, "student_imported", record)
            messages.success(request, f"Imported {len(records)} fictional students.")
            return redirect("management-student-directory")
        except ValidationError as err:
            form.add_error("csv", err)
        except IntegrityError:
            form.add_error("csv", "Duplicate student ID detected. No records were imported.")
    return page(request, "students", student_import=True, student_import_form=form, csv_header=",".join(CSV_HEADER))

@administrator
@require_http_methods(["GET"])
def sample_csv(request):
    text = ",".join(CSV_HEADER) + "\nDEMO001,Sample,Student,,7,7A,active,2026-01-27,\nDEMO002,Example,Learner,Example,10,10B,inactive,2026-01-27,\n"
    response = HttpResponse(text, content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = 'attachment; filename="rollflow-students-template.csv"'
    return response
