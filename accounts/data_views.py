"""Administrator-only publication reconciliation and local attendance review."""
import csv
import hashlib
import io
from datetime import date
from django.contrib import messages
from django.db import transaction
from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseForbidden
from django.shortcuts import render, redirect, get_object_or_404
from django.core.paginator import Paginator
from django.utils import timezone
from django.views.decorators.http import require_GET, require_http_methods
from .staff_views import administrator
from .security_service import lock_administrator, audit
from .connected_school import current, canonical
from .data_reconciliation import source_issues, compare_publications, diagnostics
from .dated_school import published_version, build_dated_candidate
from .models import (AttendanceRoll, AttendanceRevision, AttendanceTransferReview, Student,
                     ImportedTimetable, ConnectedSchoolPublication, OneSchoolArchiveBatch)


@administrator
@require_GET
def overview(request):
    pub=current()
    candidate=changes=warnings=None
    error=""
    try:
        _,candidate,_=build_dated_candidate(published_version())
        changes=compare_publications(pub,candidate)
        warnings=diagnostics(candidate)
    except (ValueError,OSError) as exc:
        error=str(exc)
    return render(request,"data_overview.html",{
        "publication":pub,"issues":source_issues(pub),"changes":changes,"warnings":warnings,"error":error,
        "history":Paginator(ConnectedSchoolPublication.objects.select_related("published_by").order_by("-published_at","-pk"),30).get_page(request.GET.get("page")),
        "batches":OneSchoolArchiveBatch.objects.order_by("-created_at")[:20]})


@administrator
@require_http_methods(["GET","POST"])
def restore(request, pk):
    """Restore only a dated snapshot that can be rebuilt exactly from current reviewed sources."""
    target=get_object_or_404(ConnectedSchoolPublication,pk=pk)
    error=""
    if request.method=="POST":
        if request.POST.get("confirm")!="yes" or request.POST.get("digest")!=target.digest:
            return HttpResponseBadRequest("Review and confirm the exact publication.")
        try:
            with transaction.atomic():
                if not lock_administrator(request.user):
                    return HttpResponseForbidden("Administrator access revoked.")
                list(ImportedTimetable.objects.select_for_update().order_by("pk"))
                list(OneSchoolArchiveBatch.objects.select_for_update().order_by("pk"))
                list(ConnectedSchoolPublication.objects.select_for_update().order_by("pk"))
                active=current()
                target=ConnectedSchoolPublication.objects.get(pk=pk)
                if target.active or (active and active.digest==target.digest):
                    raise ValueError("This publication is already active or equivalent.")
                if target.snapshot.get("source")!="dated":
                    raise ValueError("Only reviewed dated publications can be restored here.")
                sources,snapshot,digest=build_dated_candidate(published_version())
                if digest!=target.digest or sources!=target.source_batches or snapshot!=target.snapshot:
                    raise ValueError("Current sources or identities differ. Review a new publication; historical data was not restored.")
                # Never reinterpret attendance against another publication.
                if AttendanceRoll.objects.filter(lesson_date__gte=min(target.starts,active.starts if active else target.starts),
                    lesson_date__lte=max(target.ends,active.ends if active else target.ends)).exists():
                    raise ValueError("Attendance exists in the affected date range. Manual reconciliation is required.")
                ConnectedSchoolPublication.objects.filter(active=True).update(active=False)
                new=ConnectedSchoolPublication.objects.create(name=target.name,starts=target.starts,ends=target.ends,
                    source_batches=sources,snapshot=snapshot,digest=digest,published_by=request.user)
                audit(request.user,"publication_restored",before={"publication":active.pk if active else None},
                      after={"publication":new.pk,"restored_from":target.pk})
                messages.success(request,"Restored as a new reviewed publication. Existing source data was not modified.")
                return redirect("school-data-overview")
        except (ValueError,OSError) as exc:
            error=str(exc)
    return render(request,"data_restore.html",{"target":target,"error":error})


def safe_csv_cell(value):
    value=str(value)
    # Never emit spreadsheet formulas or control characters from imported identifiers.
    if not value or value.lstrip().startswith(("=","+","-","@")) or any(ord(c)<32 for c in value):
        raise ValueError("Unsafe or empty export value. Review the source identifiers.")
    return value


def transfer_content(roll, lock=False):
    if not roll.submitted_at or not roll.roster or set(roll.marks)!=set(map(str,roll.roster)):
        raise ValueError("Only complete submitted rolls can be reviewed.")
    if len(set(roll.roster))!=len(roll.roster) or any(v not in ("P","A","L") for v in roll.marks.values()):
        raise ValueError("Invalid or incomplete attendance marks.")
    latest=AttendanceRevision.objects.filter(roll=roll,revision=roll.revision).first()
    if not latest or latest.marks!=roll.marks or latest.action not in ("submit","correct") or (latest.action=="submit" and latest.actor_id!=roll.teacher_id) or (latest.action=="correct" and not latest.reason):
        raise ValueError("Submission history does not match. Administrator review required.")
    pub=roll.publication
    records=[c for c in pub.snapshot.get("classes",[]) if c.get("code")==roll.class_code]
    if len(records)!=1 or set(roll.roster)!=set(records[0].get("students",[])):
        raise ValueError("Frozen roster does not match its original publication.")
    identities=pub.snapshot.get("student_identity",{})
    qs=Student.objects.filter(pk__in=roll.roster).order_by("pk")
    if lock:
        qs=qs.select_for_update()
    students=list(qs)
    if len(students)!=len(roll.roster):
        raise ValueError("Student records changed. Review required.")
    buffer=io.StringIO(newline="")
    writer=csv.writer(buffer)
    writer.writerow(["Review_Date","Class_Code","Period","Start","Student_ID","RollFlow_Status"])
    for student in students:
        identity=identities.get(str(student.pk))
        if not identity or canonical(student.student_id)!=identity:
            raise ValueError("Student identity changed. Review required.")
        writer.writerow([safe_csv_cell(x) for x in (roll.lesson_date.isoformat(),roll.class_code,roll.period,roll.start,identity,roll.marks[str(student.pk)])])
    raw=buffer.getvalue().encode("utf-8")
    # Bind corrected review to the revision even if the marks return to an earlier value.
    digest_input=raw if latest.action=="submit" else str(roll.revision).encode()+b"\n"+raw
    return raw,hashlib.sha256(digest_input).hexdigest(),len(students)


@administrator
@require_GET
def transfer_list(request):
    try:
        day=date.fromisoformat(request.GET.get("date") or timezone.localdate().isoformat())
    except ValueError:
        return HttpResponseBadRequest("Choose a valid date.")
    rolls=AttendanceRoll.objects.filter(lesson_date=day).select_related("publication").prefetch_related("transfer_reviews").order_by("start","class_code")
    return render(request,"data_transfer_list.html",{"day":day,"rolls":Paginator(rolls,50).get_page(request.GET.get("page"))})


@administrator
@require_http_methods(["GET","POST"])
def transfer(request, pk):
    roll=get_object_or_404(AttendanceRoll.objects.select_related("publication"),pk=pk)
    error=""
    digest=""
    count=0
    try:
        if request.method=="POST":
            if request.POST.get("confirm")!="yes":
                return HttpResponseBadRequest("Review and confirm before exporting or reconciling.")
            with transaction.atomic():
                if not lock_administrator(request.user):
                    return HttpResponseForbidden("Administrator access revoked.")
                # Match attendance writer order: publication, student rows, roll.
                list(ImportedTimetable.objects.select_for_update().order_by("pk"))
                list(ConnectedSchoolPublication.objects.select_for_update().order_by("pk"))
                roll=get_object_or_404(AttendanceRoll.objects.select_related("publication"),pk=pk)
                raw,digest,count=transfer_content(roll,lock=True)
                locked=AttendanceRoll.objects.select_for_update().get(pk=pk)
                if locked.revision!=roll.revision or locked.marks!=roll.marks or request.POST.get("digest")!=digest:
                    raise ValueError("Roll or review changed. Reload before proceeding.")
                action=request.POST.get("action")
                if action=="export":
                    review,created=AttendanceTransferReview.objects.get_or_create(roll=roll,revision=roll.revision,digest=digest,
                        defaults={"row_count":count,"reviewed_by":request.user})
                    audit(request.user,"attendance_review_export",after={"review":review.pk,"roll":roll.pk,"revision":roll.revision,"rows":count})
                    response=HttpResponse(raw,content_type="text/csv; charset=utf-8")
                    response["Content-Disposition"]=f'attachment; filename="RollFlow-LOCAL-REVIEW-{roll.pk}-r{roll.revision}.csv"'
                    response["Cache-Control"]="no-store"
                    return response
                if action=="reconcile":
                    review=AttendanceTransferReview.objects.select_for_update().filter(roll=roll,revision=roll.revision,digest=digest).first()
                    if not review:
                        raise ValueError("Export and review this exact revision first.")
                    if review.reconciled_at:
                        raise ValueError("This revision has already been manually reconciled.")
                    review.reconciled_by=request.user
                    review.reconciled_at=timezone.now()
                    review.save(update_fields=["reconciled_by","reconciled_at"])
                    audit(request.user,"attendance_manual_reconcile",after={"review":review.pk,"roll":roll.pk,"revision":roll.revision})
                    return redirect("school-data-transfer",pk=pk)
                return HttpResponseBadRequest("Unknown review action.")
        else:
            _,digest,count=transfer_content(roll)
    except ValueError as exc:
        error=str(exc)
    reviews=roll.transfer_reviews.select_related("reviewed_by","reconciled_by").order_by("-reviewed_at")
    return render(request,"data_transfer.html",{"roll":roll,"digest":digest,"count":count,"error":error,"reviews":reviews})
