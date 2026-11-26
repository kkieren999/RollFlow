"""Admin publication and teacher-scoped connected school views."""
from datetime import timedelta
from django import forms
from django.contrib import messages
from django.db import IntegrityError, transaction
from django.http import HttpResponseBadRequest, HttpResponseForbidden, Http404
from django.shortcuts import redirect, render, get_object_or_404
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET, require_POST, require_http_methods
from django.core.paginator import Paginator
from django.db.models import Q
from .connected_school import (build_candidate, canonical, current, eligible_profile,
    observed_codes, mapping_valid, personal_codes, selected_day, source_set, visible_slots)
from .models import ConnectedSchoolPublication, ConnectedStaffMapping, StaffProfile, SecurityEvent, Student
from .staff_views import administrator
from .views import role_for
from .permissions import can_teach


class PublishForm(forms.Form):
    name = forms.CharField(max_length=100, label="School term / publication name")
    starts = forms.DateField(widget=forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"))
    ends = forms.DateField(widget=forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"))
    times = forms.CharField(max_length=2000, widget=forms.Textarea(attrs={
        "rows": 10, "placeholder": "Monday,1,08:50,10:00\nMonday,2,11:00,12:10\n… enter all 20 weekday/period rows"
    }), label="Lesson times (Day,Period,Start,End — no header)")
    closures = forms.CharField(required=False, max_length=2000, widget=forms.Textarea(attrs={
        "rows": 4, "placeholder": "YYYY-MM-DD (one date per line)"
    }), label="School closure / public holiday dates")


def event(request, name, subject):
    SecurityEvent.objects.create(actor=request.user, event=name, subject=str(subject)[:150])


@administrator
@require_http_methods(["GET", "POST"])
def centre(request):
    existing = current()
    initial = {}
    if existing and existing.snapshot.get("source") != "dated":
        from .connected_school import DAYS
        calendar = existing.snapshot["calendar"]
        initial = {"name": existing.name, "starts": existing.starts, "ends": existing.ends,
                   "times": "\n".join(f"{day},{period}," + ",".join(calendar["times"][f"{index}:{period}"])
                             for index, day in enumerate(DAYS, 1) for period in range(1, 5)),
                   "closures": "\n".join(calendar["closed"])}
    else:
        from .connected_school import DAYS
        initial["times"] = "\n".join(f"{day},{period},," for day in DAYS for period in range(1,5))
    if request.method == "GET" and (not existing or request.GET.get("autofill") == "1"):
        from .automated_setup import setup_candidate, suggested_csv
        try:
            suggestion = setup_candidate()
            initial["times"] = suggested_csv(suggestion)
            if not existing and suggestion["term_hint"]:
                initial["name"] = suggestion["term_hint"]
        except Exception:
            pass  # Manual calendar remains available if the source has an unsupported layout.
    form = PublishForm(request.POST if request.method == "POST" else None, initial=initial)
    preview = None
    if request.method == "POST" and form.is_valid():
        action = request.POST.get("action")
        if action not in ("review", "publish"):
            return HttpResponseBadRequest("Choose review or publish.")
        try:
            with transaction.atomic():
                sources, snapshot, digest = build_candidate(**form.cleaned_data)
                preview = {"stats": snapshot["stats"], "digest": digest, "sources": sources,
                           "examples": [{"code": c["code"], "name": c["name"], "count": len(c["students"])}
                                        for c in snapshot["classes"][:12]]}
                if action == "publish":
                    if request.POST.get("digest") != digest or request.POST.get("confirm") != "yes":
                        form.add_error(None, "Data or settings changed, or approval was missing. Review again before publication.")
                    else:
                        ConnectedSchoolPublication.objects.filter(active=True).update(active=False)
                        publication = ConnectedSchoolPublication.objects.create(
                            name=form.cleaned_data["name"], starts=form.cleaned_data["starts"],
                            ends=form.cleaned_data["ends"], source_batches=sources,
                            snapshot=snapshot, digest=digest, published_by=request.user)
                        event(request, "connected_school_published", publication.pk)
                        messages.success(request, "School data published. Existing source imports and archives are unchanged.")
                        return redirect("connected-school")
        except (ValueError, OSError) as exc:
            form.add_error(None, str(exc))
        except IntegrityError:
            form.add_error(None, "Another publication was in progress; review and retry.")
    error = ""
    batches, codes = {}, []
    try:
        batches = source_set()
        codes = sorted(observed_codes(batches))
    except ValueError as exc:
        error = str(exc)
    profiles = [p for p in StaffProfile.objects.select_related("user").filter(
        timetable_link_verified=True, user__is_active=True
    ).order_by("user__username") if eligible_profile(p)]
    mappings = list(ConnectedStaffMapping.objects.select_related("profile__user").order_by("staff_code"))
    return render(request, "connected_school.html", {
        "mode": "publish", "form": form, "preview": preview, "source_error": error,
        "batches": batches, "codes": codes, "profiles": profiles, "mappings": mappings,
        "publication": current()})


@administrator
@require_POST
def mapping(request):
    if request.POST.get("confirm") != "yes":
        return HttpResponseBadRequest("Explicit staff identity confirmation is required.")
    code = canonical(request.POST.get("staff_code"))
    try:
        with transaction.atomic():
            if request.POST.get("action") == "revoke":
                old = get_object_or_404(ConnectedStaffMapping.objects.select_for_update(), staff_code=code)
                old.delete()
                event(request, "connected_mapping_revoked", code)
                messages.success(request, "Mapping revoked immediately.")
            elif request.POST.get("action") == "verify":
                if code not in observed_codes(source_set()):
                    raise ValueError("Select a staff code from the approved source reports.")
                profile = get_object_or_404(StaffProfile.objects.select_for_update(), pk=request.POST.get("profile"))
                if not eligible_profile(profile):
                    raise ValueError("Choose an active teacher with a separately verified OneSchool staff ID.")
                if ConnectedStaffMapping.objects.filter(profile=profile).exclude(staff_code=code).exists():
                    raise ValueError("Revoke the teacher's previous code before linking a different code.")
                old = ConnectedStaffMapping.objects.filter(staff_code=code).first()
                if old and old.profile_id != profile.pk:
                    raise ValueError("Revoke the existing mapping before assigning this code to a different account.")
                ConnectedStaffMapping.objects.update_or_create(staff_code=code, defaults={
                    "profile": profile, "verified_staff_id": canonical(profile.staff_id),
                    "verified_by": request.user})
                event(request, "connected_mapping_verified", code)
                messages.success(request, "Mapping verified. Review and publish school data to activate it.")
            else:
                return HttpResponseBadRequest("Unknown mapping action.")
    except (ValueError, TypeError, IntegrityError):
        messages.error(request, "Mapping not saved. Check approved staff codes, verified teacher accounts and existing mappings.")
    return redirect("connected-school")


def publication_or_404():
    publication = current()
    if publication is None:
        raise Http404("No connected school publication.")
    return publication


@administrator
@require_GET
def classes(request):
    publication = publication_or_404()
    query = request.GET.get("q", "").strip().upper()[:100]
    classes = [c for c in publication.snapshot["classes"] if query in (c["code"] + " " + c["name"]).upper()]
    return render(request, "connected_school.html", {
        "mode": "classes", "publication": publication, "query": query,
        "classes": Paginator(classes, 50).get_page(request.GET.get("page"))})


def schedule_context(publication, request, codes=None, week=False):
    day = selected_day(publication, request.GET.get("date"))
    dates = [day]
    if week:
        monday = day - timedelta(days=day.weekday())
        dates = [monday + timedelta(days=i) for i in range(5)]
    names = {c["code"]: c["name"] for c in publication.snapshot["classes"]}
    days = []
    for d in dates:
        rows = visible_slots(publication, d, codes)
        for row in rows:
            row["name"] = row.get("name") or names[row["code"]]
            if codes is not None:
                row.pop("staff", None)
                row.pop("staff_code", None)
        days.append({"date": d, "rows": rows})
    step = timedelta(days=7 if week else 1)
    previous_date = max(publication.starts, day - step)
    next_date = min(publication.ends, day + step)
    return {"publication": publication, "day": day, "days": days,
            "previous_date": previous_date, "next_date": next_date,
            "week_view": week, "no_mapping": codes == set()}


@administrator
@require_GET
def master(request):
    return render(request, "connected_school.html", {
        "mode": "master", **schedule_context(publication_or_404(), request)})


@never_cache
@require_GET
def teacher_schedule(request, week=False):
    role = role_for(request.user)
    if role is None:
        return redirect("teacher-login")
    if not can_teach(request.user):
        return HttpResponseForbidden("Teacher access required.")
    publication = publication_or_404()
    codes = personal_codes(publication, request.user)
    context = schedule_context(publication, request, codes, week)
    if week or context["day"].weekday() < 5:
        context["days"] = schedule_context(publication, request, codes, True)["days"]
        context["native_cards"] = True
    return render(request, "connected_school.html", {"mode": "teacher", **context})


@never_cache
@require_GET
def roster(request, code, admin_only=False):
    role = role_for(request.user)
    if role is None:
        return redirect("admin-login" if admin_only else "teacher-login")
    if (admin_only and role != "admin") or (not admin_only and not can_teach(request.user)):
        return HttpResponseForbidden("Access denied.")
    publication = publication_or_404()
    code = canonical(code)
    today = timezone.localdate()
    if not admin_only:
        codes = personal_codes(publication, request.user)
        if publication.snapshot.get("source") == "dated":
            try:
                from datetime import date
                assigned_date = date.fromisoformat(request.GET.get("date") or today.isoformat())
            except ValueError:
                return HttpResponseForbidden("Invalid allocation date.")
            assigned = any(s["code"] == code for s in visible_slots(publication, assigned_date, codes))
        else:
            assigned = any(s["code"] == code and s["staff"] in codes for s in publication.snapshot["slots"])
        if not publication.starts <= today <= publication.ends or not assigned:
            return HttpResponseForbidden("This class is not in your current verified publication for the requested date.")
    record = next((c for c in publication.snapshot["classes"] if c["code"] == code), None)
    if record is None:
        raise Http404("Unknown published class.")
    students = Student.objects.filter(pk__in=record["students"], status=Student.Status.ACTIVE).filter(
        Q(enrolled_on__isnull=True) | Q(enrolled_on__lte=today)
    ).filter(Q(left_on__isnull=True) | Q(left_on__gte=today)).order_by("last_name", "first_name", "pk")
    identity = publication.snapshot.get("student_identity", {})
    students = [s for s in students if canonical(s.student_id) == identity.get(str(s.pk))]
    return render(request, "connected_school.html", {
        "mode": "roster", "publication": publication, "record": record,
        "students": Paginator(students, 50).get_page(request.GET.get("page")),
        "admin_roster": admin_only, "roster_date": request.GET.get("date", "")})

@administrator
@require_http_methods(["GET", "POST"])
def dated_centre(request):
    """Explicit review/publish of the dated timetable and approved roster source set."""
    import re
    from datetime import date
    from django.contrib.auth.models import User
    from .dated_school import published_version, build_dated_candidate
    from .data_reconciliation import compare_publications, diagnostics
    from .models import ImportedTimetable
    version = published_version()
    preview = None
    error = ""
    try:
        with transaction.atomic():
            if request.method == "POST":
                # Serialize against dated import publication and concurrent refreshes.
                list(ImportedTimetable.objects.select_for_update().order_by("pk").values_list("pk", flat=True))
                version = published_version()
            sources, snapshot, digest = build_dated_candidate(version)
            preview = {"stats": snapshot["stats"], "digest": digest,
                       "starts": snapshot["calendar"]["dates"][0],
                       "ends": snapshot["calendar"]["dates"][-1],
                       "changes": compare_publications(current(), snapshot), "diagnostics": diagnostics(snapshot)}
            if request.method == "POST":
                action = request.POST.get("action")
                if action not in ("publish", "prepare"):
                    return HttpResponseBadRequest("Unknown publication action.")
                if request.POST.get("digest") != digest or request.POST.get("confirm") != "yes":
                    raise ValueError("Data or settings changed, or approval was missing. Review the latest preview again.")
                if action == "prepare":
                    count = 0
                    for key in snapshot["stats"]["missing_profiles"]:
                        # No names, MISIDs, password guesses, or automatic activation.
                        if not re.fullmatch(r"[A-Z0-9_.-]{1,40}", key):
                            continue
                        username = "oneschool-" + key.lower()
                        if (User.objects.filter(username__iexact=username).exists() or
                                StaffProfile.objects.filter(staff_id__iexact=key).exists()):
                            continue
                        user = User.objects.create_user(username=username, is_active=False)
                        StaffProfile.objects.create(user=user, staff_id=key, timetable_link_verified=False,
                                                    teaching_enabled=False)
                        event(request, "dated_staff_prepared", user.username)
                        count += 1
                    messages.success(request, f"Prepared {count} inactive staff accounts. Verify identity, set a password, grant teaching and activate separately.")
                else:
                    list(ConnectedSchoolPublication.objects.select_for_update().order_by("pk").values_list("pk", flat=True))
                    active = current()
                    if active and active.digest == digest:
                        messages.info(request, "This exact reviewed publication is already active. Existing attendance was preserved.")
                        return redirect("connected-dated")
                    if active and __import__("accounts.models", fromlist=["AttendanceRoll"]).AttendanceRoll.objects.filter(publication=active).exists() and request.POST.get("acknowledge_rolls") != "yes":
                        raise ValueError("Existing attendance refers to this publication. Review the impact and explicitly acknowledge before replacement.")
                    ConnectedSchoolPublication.objects.filter(active=True).update(active=False)
                    publication = ConnectedSchoolPublication.objects.create(
                        name=version.name, starts=date.fromisoformat(preview["starts"]),
                        ends=date.fromisoformat(preview["ends"]), source_batches=sources,
                        snapshot=snapshot, digest=digest, published_by=request.user)
                    event(request, "dated_school_published", publication.pk)
                    messages.success(request, "Dated school timetable published. It is now the authoritative connected school snapshot.")
                return redirect("connected-dated")
    except (ValueError, OSError) as exc:
        error = str(exc)
    except IntegrityError:
        error = "A concurrent school update occurred. Review and retry."
    return render(request, "connected_dated.html", {
        "version": version, "preview": preview, "error": error, "publication": current()})
