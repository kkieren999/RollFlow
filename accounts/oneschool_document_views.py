"""Administrator-only offline source archive and cautious SM110 import workflow."""
import hashlib
from django import forms
from django.conf import settings
from django.contrib import messages
from django.db import IntegrityError, transaction
from django.db.models import Count
from django.core.paginator import Paginator
from django.http import Http404, HttpResponse, HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.http import content_disposition_header
from django.views.decorators.http import require_GET, require_POST, require_http_methods
from django.views.decorators.cache import never_cache

from .models import OneSchoolArchiveBatch, OneSchoolArchivedFile, OneSchoolClassMembership, Student, SecurityEvent
from .oneschool_documents import (
    ALLOWED, MAX_BATCH_SIZE, MAX_FILE_SIZE, MAX_FILES, file_name,
    inspect_file, parse_students,
)
from .oneschool_class_csv import parse_student_classes
from .oneschool_class_service import preview_links, apply_links
from .oneschool_storage import save_encrypted, read_encrypted, forget_encrypted
from .staff_views import administrator
from .oneschool_source_review import alignment_preview, staff_pdf_preview
from .models import OneSchoolLineAllocation, OneSchoolStaffClassReference


class SourceForm(forms.Form):
    kind = forms.ChoiceField(
        choices=OneSchoolArchiveBatch.Kind.choices,
        label="Which OneSchool export are you uploading?",
    )
    label = forms.CharField(
        label="Import reference", max_length=120,
        help_text="Example: Term 4 timetable, week beginning 23 November (no student names).",
    )
    acknowledge = forms.BooleanField(
        label="These files contain fictional or approved de-identified development data.",
        required=True,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if settings.ROLLFLOW_SCHOOL_MODE:
            self.fields["acknowledge"].label = (
                "I have school ICT authorisation to handle these exports in this protected instance."
            )


def event(request, kind, batch):
    SecurityEvent.objects.create(actor=request.user, event=kind, subject=str(batch.pk))


def archive_page(request, **kwargs):
    return render(request, "oneschool_documents.html", {
        "class_preview": kwargs.get("class_preview"),
        "alignment_review": kwargs.get("alignment_review"),
        "staff_review": kwargs.get("staff_review"),
        "preview_error": kwargs.get("preview_error"),
        "form": kwargs.get("form") or SourceForm(),
        "batch": kwargs.get("batch"),
        "batches": OneSchoolArchiveBatch.objects.select_related("created_by").all()[:50],
        "file_details": kwargs.get("file_details", []),
        "live_timetable": settings.ROLLFLOW_LIVE_TIMETABLE,
    })


@administrator
@require_http_methods(["GET", "POST"])
def centre(request):
    if request.method == "GET":
        return archive_page(request)
    form = SourceForm(request.POST)
    uploaded = request.FILES.getlist("files")
    if form.is_valid():
        kind = form.cleaned_data["kind"]
        if not uploaded or len(uploaded) > MAX_FILES:
            form.add_error(None, f"Select 1 to {MAX_FILES} export files.")
        elif kind in ("students", "class_members", "staff_pdf") and len(uploaded) != 1:
            form.add_error(None, "Select exactly one SM110, ExportStudentClass or whole-staff PDF file. Upload TTLine XLSX parts together.")
        elif sum(x.size for x in uploaded) > MAX_BATCH_SIZE:
            form.add_error(None, "Total upload size must be below 48 MB.")
        else:
            files, seen, saved = [], set(), []
            try:
                # Validate the entire upload BEFORE any file is archived or DB row created.
                for upload in uploaded:
                    if upload.size > MAX_FILE_SIZE:
                        raise ValueError("Each file must be 12 MB or smaller.")
                    raw = upload.read(MAX_FILE_SIZE + 1)
                    info, summary = inspect_file(kind, upload.name, raw)
                    if info["sha256"] in seen:
                        raise ValueError("The same file was selected twice in this batch.")
                    seen.add(info["sha256"])
                    files.append((raw, info, summary))
                metadata = {
                    "file_count": len(files),
                    "bytes": sum(info["size"] for _, info, _ in files),
                    "files": [
                        {"format": info["extension"], **detail}
                        for _, info, detail in files
                    ],
                    "automatic_teacher_assignment": False,
                    "subject_student_enrolment": False,
                }
                if kind in ("students", "class_members"):
                    metadata.update(files[0][2])
                    if kind == "class_members":
                        metadata["note"] = (
                            "Review EQID/Class_Name matches before applying. "
                            "Unmatched IDs or classes will never be fabricated."
                        )
                else:
                    metadata["note"] = (
                        "Archive and format review only. No staff IDs, class allocations "
                        "or student subject enrolments are changed by these files."
                    )
                with transaction.atomic():
                    batch = OneSchoolArchiveBatch.objects.create(
                        kind=kind, label=form.cleaned_data["label"],
                        summary=metadata, created_by=request.user,
                    )
                    for raw, info, _ in files:
                        token = save_encrypted(raw)
                        saved.append(token)
                        OneSchoolArchivedFile.objects.create(
                            batch=batch, original_name=info["name"],
                            storage_token=token, size=info["size"],
                            sha256=info["sha256"], format=info["extension"],
                        )
                    event(request, "oneschool_source_staged", batch)
            except (ValueError, OSError, IntegrityError) as exc:
                if saved:
                    forget_encrypted(saved)
                form.add_error(None, str(exc) if isinstance(exc, ValueError)
                               else "Import archive unavailable. No files were imported.")
            else:
                messages.success(request, "Files encrypted and staged locally. Review before applying.")
                return redirect("oneschool-documents-review", pk=batch.pk)
    return archive_page(request, form=form)


@administrator
@require_GET
def review(request, pk):
    batch = get_object_or_404(
        OneSchoolArchiveBatch.objects.select_related("created_by").prefetch_related("files"), pk=pk
    )
    if batch.kind == OneSchoolArchiveBatch.Kind.CLASS_MEMBERS and batch.status == "staged":
        if batch.source_purged_at:
            return archive_page(request, batch=batch, preview_error="The original file has been purged.")
        try:
            source = batch.files.get()
            raw = read_encrypted(source.storage_token)
            if hashlib.sha256(raw).hexdigest() != source.sha256:
                raise ValueError("Archive integrity check failed.")
            pairs, _ = parse_student_classes(raw)
            preview = preview_links(pairs)
        except (ValueError, OSError, OneSchoolArchivedFile.DoesNotExist,
                OneSchoolArchivedFile.MultipleObjectsReturned) as exc:
            return archive_page(request, batch=batch,
                                preview_error="Unable to validate archived source: " + str(exc))
        return archive_page(request, batch=batch, class_preview=preview)
    if batch.status == "staged" and batch.kind == OneSchoolArchiveBatch.Kind.TT_ALIGNMENT:
        try:
            _, preview = alignment_preview(batch)
            return archive_page(request, batch=batch, alignment_review=preview)
        except (ValueError, OSError) as exc:
            return archive_page(request, batch=batch, preview_error=str(exc))
    if batch.status == "staged" and batch.kind == OneSchoolArchiveBatch.Kind.STAFF_PDF:
        try:
            _, preview = staff_pdf_preview(batch)
            return archive_page(request, batch=batch, staff_review=preview)
        except (ValueError, OSError) as exc:
            return archive_page(request, batch=batch, preview_error=str(exc))
    return archive_page(request, batch=batch)


@administrator
@require_POST
def apply_students(request, pk):
    if request.POST.get("confirm_apply") != "yes":
        return HttpResponseBadRequest("Review and confirm the student directory changes.")
    try:
        with transaction.atomic():
            batch = get_object_or_404(OneSchoolArchiveBatch.objects.select_for_update(), pk=pk)
            if batch.kind != OneSchoolArchiveBatch.Kind.STUDENTS or batch.status != "staged" or batch.source_purged_at:
                return HttpResponseBadRequest("This archive is not an unapplied SM110 import.")
            source = get_object_or_404(OneSchoolArchivedFile, batch=batch)
            raw = read_encrypted(source.storage_token)
            if hashlib.sha256(raw).hexdigest() != source.sha256:
                raise ValueError("Original import integrity check failed.")
            records, latest_summary = parse_students(raw)
            created = updated = unchanged = 0
            for row in records:
                existing = list(Student.objects.select_for_update().filter(
                    student_id__iexact=row["student_id"]
                )[:2])
                if len(existing) > 1:
                    raise ValueError("Conflicting student identifiers need administrator review.")
                if not existing:
                    Student.objects.create(
                        **row, status=Student.Status.ACTIVE,
                    )
                    created += 1
                else:
                    student = existing[0]
                    updates = []
                    # Never modify historical status, leave dates, photos or
                    # subject-class enrolments from a simple active SM110 export.
                    for field in ("first_name", "last_name", "year_level", "home_group"):
                        if getattr(student, field) != row[field]:
                            setattr(student, field, row[field])
                            updates.append(field)
                    if updates:
                        student.save(update_fields=updates + ["updated_at"])
                        updated += 1
                    else:
                        unchanged += 1
            batch.summary = {
                **batch.summary,
                **latest_summary,
                "applied": {"created": created, "updated": updated, "unchanged": unchanged},
            }
            batch.status = OneSchoolArchiveBatch.Status.APPLIED
            batch.applied_at = timezone.now()
            batch.save(update_fields=["summary", "status", "applied_at"])
            event(request, "oneschool_students_applied", batch)
    except (ValueError, OSError) as exc:
        messages.error(request, str(exc))
        return redirect("oneschool-documents-review", pk=pk)
    except IntegrityError:
        messages.error(request, "Conflicting student records detected. No changes were applied.")
        return redirect("oneschool-documents-review", pk=pk)
    messages.success(
        request, f"Student directory updated: {created} new, {updated} changed, {unchanged} unchanged. "
                 "Subject class enrolments were not modified."
    )
    return redirect("oneschool-documents-review", pk=pk)


@administrator
@require_POST
def apply_class_memberships(request, pk):
    # Confirm the exact reviewed match set, not a changed class catalogue.
    if request.POST.get("confirm_apply") != "yes":
        return HttpResponseBadRequest("Confirm before applying class memberships.")
    try:
        with transaction.atomic():
            batch = get_object_or_404(
                OneSchoolArchiveBatch.objects.select_for_update(), pk=pk
            )
            if (batch.kind != OneSchoolArchiveBatch.Kind.CLASS_MEMBERS
                    or batch.status != "staged" or batch.source_purged_at):
                return HttpResponseBadRequest("This is not a pending student-class export.")
            source = get_object_or_404(OneSchoolArchivedFile, batch=batch)
            raw = read_encrypted(source.storage_token)
            if hashlib.sha256(raw).hexdigest() != source.sha256:
                raise ValueError("Archived source checksum mismatch.")
            pairs, parsed = parse_student_classes(raw)
            preview = preview_links(pairs)
            if request.POST.get("preview_signature") != preview["preview_signature"]:
                messages.error(request, "The student or class records changed. Review the matches again.")
                return redirect("oneschool-documents-review", pk=pk)
            if preview["skipped_count"] and request.POST.get("skip_unmatched") != "yes":
                messages.error(request, "Review and acknowledge unmatched rows before applying.")
                return redirect("oneschool-documents-review", pk=pk)
            if not preview["matched_count"]:
                messages.error(request, "There are no matching student-class pairs to apply.")
                return redirect("oneschool-documents-review", pk=pk)
            applied = apply_links(preview["matched"], batch)
            batch.summary = {**batch.summary, **parsed,
                "subject_student_enrolment": True,
                "applied": {
                **applied,
                "skipped": preview["skipped_count"],
                "matched": preview["matched_count"],
                "unmatched_students": preview["unmatched_student_count"],
                "inactive_students": preview["inactive_student_count"],
                "unmatched_classes": preview["unmatched_class_count"],
            }}
            batch.status = OneSchoolArchiveBatch.Status.APPLIED
            batch.applied_at = timezone.now()
            batch.save(update_fields=["summary", "status", "applied_at"])
            event(request, "oneschool_classes_applied", batch)
    except (ValueError, OSError) as exc:
        messages.error(request, str(exc))
        return redirect("oneschool-documents-review", pk=pk)
    except IntegrityError:
        messages.error(request, "Student/class membership conflict. No changes were applied.")
        return redirect("oneschool-documents-review", pk=pk)
    messages.success(request,
        f"Student-class links applied: {applied['created']} new, "
        f"{applied['already_present']} already present, "
        f"{preview['skipped_count']} unmatched rows not applied. "
        "No student accounts or teacher assignments were changed."
    )
    return redirect("oneschool-documents-review", pk=pk)


@administrator
@require_POST
def apply_alignment(request, pk):
    if request.POST.get("confirm_apply") != "yes":
        return HttpResponseBadRequest("Confirm the timetable line import before applying.")
    try:
        with transaction.atomic():
            batch = get_object_or_404(
                OneSchoolArchiveBatch.objects.select_for_update(), pk=pk
            )
            if batch.kind != OneSchoolArchiveBatch.Kind.TT_ALIGNMENT or batch.status != "staged" or batch.source_purged_at:
                return HttpResponseBadRequest("This is not a pending TTLine upload.")
            rows, preview = alignment_preview(batch)
            if not preview["complete"]:
                messages.error(request, "Missing TTLine exports: upload all seven line files in a single batch.")
                return redirect("oneschool-documents-review", pk=pk)
            if request.POST.get("source_signature") != preview["source_signature"]:
                messages.error(request, "Sources changed. Review the seven alignment files again.")
                return redirect("oneschool-documents-review", pk=pk)
            OneSchoolLineAllocation.objects.bulk_create(
                [OneSchoolLineAllocation(batch=batch, **record) for record in rows],
                batch_size=300,
            )
            batch.summary = {
                **batch.summary,
                "applied": {
                    "timetable_version_id": preview["timetable_version_id"],
                    "lines": preview["lines"],
                    "allocations": preview["allocation_count"],
                    "classes": preview["distinct_classes"],
                    "staff_code_count": preview["staff_codes"],
                    "unallocated_staff": preview["unallocated_staff"],
                },
                "verified_timetable_line_schema": True,
            }
            batch.status = OneSchoolArchiveBatch.Status.APPLIED
            batch.applied_at = timezone.now()
            batch.save(update_fields=["summary", "status", "applied_at"])
            event(request, "oneschool_alignment_applied", batch)
    except (ValueError, OSError) as exc:
        messages.error(request, str(exc))
        return redirect("oneschool-documents-review", pk=pk)
    except IntegrityError:
        messages.error(request, "Conflicting class/day/period records; no timetable lines were applied.")
        return redirect("oneschool-documents-review", pk=pk)
    messages.success(request,
        f"Seven timetable lines verified and saved: {preview['allocation_count']} class slots. "
        "Staff codes remain unverified evidence, not teacher account assignments."
    )
    return redirect("oneschool-documents-review", pk=pk)


@administrator
@require_POST
def apply_staff_pdf(request, pk):
    if request.POST.get("confirm_apply") != "yes":
        return HttpResponseBadRequest("Confirm staff PDF evidence import.")
    try:
        with transaction.atomic():
            batch = get_object_or_404(
                OneSchoolArchiveBatch.objects.select_for_update(), pk=pk
            )
            if batch.kind != OneSchoolArchiveBatch.Kind.STAFF_PDF or batch.status != "staged" or batch.source_purged_at:
                return HttpResponseBadRequest("This is not a pending staff PDF.")
            rows, preview = staff_pdf_preview(batch)
            if request.POST.get("source_signature") != preview["source_signature"]:
                messages.error(request, "Staff PDF source changed. Review it again.")
                return redirect("oneschool-documents-review", pk=pk)
            if preview["pages_without_legend"] and request.POST.get("acknowledge_empty_pages") != "yes":
                messages.error(request, "Acknowledge the pages without readable class legends.")
                return redirect("oneschool-documents-review", pk=pk)
            OneSchoolStaffClassReference.objects.bulk_create(
                [OneSchoolStaffClassReference(batch=batch, **record) for record in rows],
                batch_size=300,
            )
            batch.summary = {
                **batch.summary,
                "applied": {
                    "pages": preview["pages"],
                    "staff_codes": preview["staff_codes"],
                    "class_references": preview["staff_class_references"],
                    "classes": preview["distinct_classes"],
                    "pages_without_legend": preview["pages_without_legend"],
                    "timetable_version_id": preview["timetable_version_id"],
                },
                "verified_staff_pdf_layout": True,
                "teacher_account_permission_grants": False,
            }
            batch.status = OneSchoolArchiveBatch.Status.APPLIED
            batch.applied_at = timezone.now()
            batch.save(update_fields=["summary", "status", "applied_at"])
            event(request, "oneschool_staff_pdf_applied", batch)
    except (ValueError, OSError) as exc:
        messages.error(request, str(exc))
        return redirect("oneschool-documents-review", pk=pk)
    except IntegrityError:
        messages.error(request, "Duplicate or conflicting staff class references; no PDF evidence was applied.")
        return redirect("oneschool-documents-review", pk=pk)
    messages.success(request,
        f"Staff PDF evidence saved: {preview['staff_class_references']} class references. "
        "No teacher account identity or permissions were changed."
    )
    return redirect("oneschool-documents-review", pk=pk)


@administrator
@require_GET
def download(request, pk):
    item = get_object_or_404(
        OneSchoolArchivedFile.objects.select_related("batch"), pk=pk
    )
    if item.batch.source_purged_at:
        raise Http404("Original source was securely removed.")
    try:
        raw = read_encrypted(item.storage_token)
        if hashlib.sha256(raw).hexdigest() != item.sha256:
            raise ValueError("Archive digest mismatch.")
    except ValueError:
        raise Http404("Archived source could not be verified.") from None
    event(request, "oneschool_source_download", item.batch)
    response = HttpResponse(raw, content_type="application/octet-stream")
    response["Content-Disposition"] = content_disposition_header(
        as_attachment=True, filename=file_name(item.original_name)
    )
    response["Cache-Control"] = "private, no-store, max-age=0"
    response["X-Content-Type-Options"] = "nosniff"
    return response


@administrator
@require_POST
def purge(request, pk):
    if request.POST.get("confirm_purge") != "DELETE SOURCES":
        return HttpResponseBadRequest("Confirm irreversible source deletion.")
    with transaction.atomic():
        batch = get_object_or_404(
            OneSchoolArchiveBatch.objects.select_for_update().prefetch_related("files"), pk=pk
        )
        if not batch.source_purged_at:
            tokens = [f.storage_token for f in batch.files.all()]
            batch.source_purged_at = timezone.now()
            batch.save(update_fields=["source_purged_at"])
            event(request, "oneschool_sources_purged", batch)
            transaction.on_commit(lambda: forget_encrypted(tokens))
    messages.success(request, "Encrypted source copies deleted. Audit metadata retained.")
    return redirect("oneschool-documents-review", pk=pk)



@administrator
@never_cache
@require_GET
def class_rosters(request):
    """Admin-only read-only check of imported student/class relationships."""
    q = request.GET.get("class", "").strip().upper()[:30]
    overview = OneSchoolClassMembership.objects.values("class_code").annotate(
        member_count=Count("student_id")
    ).order_by("class_code")[:200]
    members = None
    if q and all(x.isascii() and (x.isalnum() or x in "_-") for x in q):
        matches = OneSchoolClassMembership.objects.filter(class_code=q).select_related(
            "student", "source_batch"
        ).order_by("student__last_name", "student__first_name", "student__student_id")
        members = Paginator(matches, 50).get_page(request.GET.get("page"))
    return render(request, "oneschool_class_rosters.html", {
        "overview": overview, "class_code": q, "members": members,
    })
