"""Administrator-only review and provisioning. Never infer identity."""
import re
from django.contrib import messages
from django.contrib.auth.models import Group, User
from django.db import IntegrityError, transaction
from django.http import HttpResponseBadRequest
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods
from .automated_setup import setup_candidate
from .models import ConnectedStaffMapping, PendingTeacherSetup, StaffProfile, SecurityEvent
from .staff_views import administrator
from .connected_school import canonical

def account_rows(candidate):
    pending={p.staff_code:p for p in PendingTeacherSetup.objects.select_related("user")}
    mapped=set(ConnectedStaffMapping.objects.values_list("staff_code",flat=True))
    usernames={s.casefold() for s in User.objects.values_list("username",flat=True)}
    ids={canonical(s) for s in StaffProfile.objects.values_list("staff_id",flat=True)}
    rows=[]
    for person in candidate["people"]:
        code=person["code"]
        item=dict(person,username="rf-"+code.lower(),pending=pending.get(code))
        p=item["pending"]
        if p:
            item["state"]="Activated" if p.activated_at else "Pending"
            item["ready"]=bool(not p.activated_at and not p.user.is_active and p.user.has_usable_password())
        elif code in mapped or code in ids or item["username"].casefold() in usernames:
            item["state"]="Existing account or identity conflict — review manually"
        else:
            item["state"]="New disabled account"
        rows.append(item)
    return rows

@administrator
@require_http_methods(["GET","POST"])
def setup(request):
    try:
        candidate=setup_candidate()
    except (ValueError,OSError) as exc:
        return render(request,"automated_setup.html",{"error":str(exc)})
    except Exception:
        return render(request,"automated_setup.html",{"error":"Unable to safely extract the archived PDF. Review the original report."})
    rows=account_rows(candidate)
    if request.method=="POST":
        if request.POST.get("confirm")!="yes" or request.POST.get("digest")!=candidate["digest"]:
            return HttpResponseBadRequest("Review the current sources and confirm before changing accounts.")
        action=request.POST.get("action")
        selected=set(request.POST.getlist("selected"))
        by_code={r["code"]:r for r in rows}
        if action not in ("prepare","activate") or not selected or not selected<=set(by_code):
            return HttpResponseBadRequest("Select valid staff rows and action.")
        try:
            with transaction.atomic():
                if action=="prepare":
                    for code in sorted(selected):
                        row=by_code[code]
                        if row["state"]!="New disabled account":
                            raise ValueError("Existing account; refresh and review.")
                        if (User.objects.filter(username__iexact=row["username"]).exists()
                            or StaffProfile.objects.filter(staff_id__iexact=code).exists()
                            or ConnectedStaffMapping.objects.filter(staff_code=code).exists()):
                            raise ValueError("Existing account or mapping conflict.")
                        user=User(username=row["username"],first_name=row["first"],last_name=row["last"],
                                  is_active=False,is_staff=False,is_superuser=False)
                        user.set_unusable_password()
                        user.save()
                        user.groups.add(Group.objects.get(name="Teacher"))
                        StaffProfile.objects.create(user=user,timetable_link_verified=False)
                        PendingTeacherSetup.objects.create(staff_code=code,user=user,
                            source_batch_id=candidate["source_batch"],created_by=request.user)
                        SecurityEvent.objects.create(actor=request.user,event="pending_teacher_created",subject=user.username)
                    messages.success(request,f"{len(selected)} disabled accounts prepared. No passwords or access granted.")
                else:
                    official_ids=set()
                    for code in sorted(selected):
                        item=by_code[code]
                        pending=PendingTeacherSetup.objects.select_for_update().get(staff_code=code)
                        user=User.objects.select_for_update().get(pk=pending.user_id)
                        profile=StaffProfile.objects.select_for_update().get(user=user)
                        staff_id=canonical(request.POST.get("id_"+code))
                        if (not re.fullmatch(r"[A-Z0-9_-]{1,40}",staff_id)
                            or request.POST.get("verify_"+code)!="yes"):
                            raise ValueError("Enter each selected official Staff ID and attest to identity verification.")
                        if (pending.activated_at or user.is_active or user.is_staff or user.is_superuser
                            or not user.has_usable_password()
                            or set(user.groups.values_list("name",flat=True))!={"Teacher"}
                            or user.user_permissions.exists()
                            or user.first_name!=item["first"] or user.last_name!=item["last"]
                            or profile.staff_id or profile.timetable_link_verified
                            or ConnectedStaffMapping.objects.filter(profile=profile).exists()):
                            raise ValueError("Selected account is not a valid pending teacher with a password and matching identity.")
                        if (staff_id in official_ids or StaffProfile.objects.filter(staff_id__iexact=staff_id).exists()
                            or ConnectedStaffMapping.objects.filter(staff_code=code).exists()):
                            raise ValueError("Staff ID or printed-code mapping is already in use.")
                        official_ids.add(staff_id)
                        profile.staff_id=staff_id
                        profile.timetable_link_verified=True
                        profile.save(update_fields=["staff_id","timetable_link_verified"])
                        user.is_active=True
                        user.save(update_fields=["is_active"])
                        ConnectedStaffMapping.objects.create(staff_code=code,profile=profile,
                            verified_staff_id=staff_id,verified_by=request.user)
                        pending.activated_at=timezone.now()
                        pending.activated_by=request.user
                        pending.save(update_fields=["activated_at","activated_by"])
                        SecurityEvent.objects.create(actor=request.user,event="pending_teacher_activated",subject=user.username)
                    messages.success(request,f"{len(selected)} accounts verified and activated. Review and republish to enable connected rosters.")
        except (ValueError,IntegrityError,PendingTeacherSetup.DoesNotExist,StaffProfile.DoesNotExist):
            messages.error(request,"No changes applied. Check selected accounts, password readiness, verified IDs and conflicts.")
        return redirect("automated-school-setup")
    return render(request,"automated_setup.html",{"candidate":candidate,"rows":rows})
