"""Protected presentation context; existing views remain authorization boundaries."""
from django.conf import settings
from django.urls import reverse
from django.utils import timezone
from .security_service import eligible_account
from .live_views import shell
from .models import WorkforceNotice


def workspace_context(request):
    if not settings.ROLLFLOW_PROTECTED_WORKSPACE:
        return {}
    result={"rf_ui_enabled":True}
    if not eligible_account(request.user):
        return result
    ctx=shell(request.user)
    if not (ctx["teaching"] or ctx["admin_access"] or ctx["grants"]):
        return result
    path=request.path
    groups=[]
    def link(label,name,kwargs=None,aliases=()):
        url=reverse(name,kwargs=kwargs)
        return {"label":label,"url":url,"active":path==url or any(path.startswith(a) for a in aliases)}
    def group(section,label,icon,*links):
        if links:
            groups.append({"section":section,"label":label,"icon":icon,"url":links[0]["url"],
                           "active":any(x["active"] for x in links),"links":links})
    def directory(code,label):
        return link(label,"school-workspace-module",{"module":code})
    teaching,admin=ctx["teaching"],ctx["admin_access"]
    caps=set(ctx["modules"])
    if admin:
        group("SCHOOL MANAGEMENT","Dashboard","home",link("Dashboard","management-dashboard"),link("Administration portal","admin-system-centre"),link("Staff workspace","live-home"))
    elif not teaching:
        group("WORKSPACE","Dashboard","home",link("Dashboard","live-home",aliases=("/workspace/",) if path=="/workspace/" else ()))
    if teaching:
        group("TEACHING","Daily Schedule","calendar",link("Daily schedule","live-day",aliases=("/live/roll/","/live/classroom/","/live/movements/issue/","/teacher/timetable/")),
              link("Weekly timetable","teacher-week"))
    if teaching:
        group("TEACHING","Master Timetable","calendar",link("My verified allocations","teacher-personal-master"),*[directory(c,l) for c,l in (("published_timetable","Published timetable"),("timetable","Manual timetable")) if c in caps])
        group("TEACHING","Class Finder","list",link("My classes","teacher-class-finder",aliases=("/live/teacher/classes/","/teacher/roster/")),*[directory(c,l) for c,l in (("published_classes","Published classes"),("classes","Manual classes")) if c in caps])
        group("TEACHING","Student Search","search",link("My students","teacher-student-search",aliases=("/live/teacher/students/",)),*([directory("students","Scoped student directory")] if "students" in caps else []))
    if admin:
        group("SCHOOL MANAGEMENT","Staff Management","users",link("Staff directory","management-section",{"section":"staff"},("/manage/staff/",)))
        group("SCHOOL MANAGEMENT","Student Management","users",link("Student directory","management-student-directory",aliases=("/manage/students/",)))
        group("SCHOOL MANAGEMENT","Timetable Management","calendar",link("Timetable","management-timetable",aliases=("/manage/timetable/","/manage/rooms/","/manage/periods/")),
              link("Master timetable","management-master",aliases=("/manage/connected/master/",)),
              link("Class directory","management-class-directory",aliases=("/manage/classes/","/manage/enrolments/","/manage/connected/classes/","/manage/connected/roster/")))
    elif not teaching:
        group("WORKSPACE","Master Timetable","calendar",*[directory(c,l) for c,l in (("published_timetable","Published timetable"),("timetable","Manual timetable")) if c in caps])
        group("WORKSPACE","Class Finder","list",*[directory(c,l) for c,l in (("published_classes","Published classes"),("classes","Manual classes")) if c in caps])
        if "students" in caps:group("WORKSPACE","Student Search","search",directory("students","Student directory"))
    if not admin and "staff" in caps:group("WORKSPACE","Staff Directory","users",directory("staff","Staff directory"))
    if ctx["monitor"]:
        group("STUDENT MANAGEMENT","Attendance Overview","check",link("Attendance overview","live-monitor"),
              *([link("Student history","attendance-student-report"),link("Attendance reconciliation","school-data-transfers",aliases=("/manage/school-data/transfers/",)),
                 link("Relief attendance","attendance-relief")] if admin else []))
    if ctx["movements"]:
        group("STUDENT MANAGEMENT","Student Movements","arrows",link("Movement register","movement-board",aliases=("/live/movements/",) if not path.startswith("/live/movements/issue/") else ()),
              *([link("Destinations","movement-destinations")] if admin else []))
    if ctx["support_access"]:
        group("STUDENT MANAGEMENT","Student Support","heart",link("Support tasks and referrals","support-board"))
    if ctx["workforce_monitor"] or ctx["workforce_self"]:
        group("OPERATIONS","Workforce Allocations","users",
              *([link("Workforce overview","workforce-board")] if ctx["workforce_monitor"] else []),
              *([link("My workforce & notices","workforce-mine")] if ctx["workforce_self"] else []))
    if ctx["report_access"]:
        group("REPORTING","Reports","chart",link("Leadership overview","leadership-overview"),link("Leadership reports","leadership-reports"))
    if admin:
        group("SYSTEM","Account Management","shield",link("Account review","admin-account-review"),link("Roles & permissions","school-access-manage"),link("Role templates","security-templates"),
              link("Access review","security-history",aliases=("/manage/security/effective/",)))
        group("SYSTEM","Audit & Activity","list",link("Activity log","admin-audit-review"),link("Structured access history","security-history"),link("Legacy activity log","management-section",{"section":"audit"}))
        group("SYSTEM","System Management","database",link("System settings & readiness","admin-system-settings"))
        group("SYSTEM","OneSchool Import Centre","database",link("Document imports","oneschool-documents",aliases=("/manage/oneschool/documents/",)),
              link("Timetable imports","oneschool-centre",aliases=("/manage/oneschool/",) if path.startswith("/manage/oneschool/") and not path.startswith(("/manage/oneschool/documents/","/manage/oneschool/class-memberships/","/manage/oneschool/timetable-evidence/")) else ()),
              link("Class memberships","oneschool-class-rosters"),link("Timetable evidence","oneschool-timetable-evidence"),
              link("School data centre","school-data-overview",aliases=("/manage/school-data/restore/",)),link("Publish dated school data","connected-dated"),
              link("Review connected data","connected-school",aliases=("/manage/connected/mapping/",)),link("Automated setup","automated-school-setup"))
        for code,label in (("staff","Staff directory"),("students","Student directory"),("published_classes","Published classes"),("published_timetable","Published timetable"),("classes","Manual classes"),("timetable","Manual timetable")):
            if code in caps:group("ASSIGNED WORKSPACE",label,"list",directory(code,label))
    exact=[(g,l) for g in groups for l in g["links"] if l["url"]==path]
    active=exact[0] if exact else next(((g,l) for g in groups for l in g["links"] if l["active"]),None)
    for g in groups:
        g["active"]=bool(active and active[0] is g)
        for l in g["links"]:l["active"]=bool(active and active[1] is l)
    sections=[]
    for g in groups:
        section=next((s for s in sections if s["label"]==g["section"]),None)
        if not section:
            section={"label":g["section"],"groups":[]}
            sections.append(section)
        section["groups"].append(g)
    roles=list(dict.fromkeys(g.role for g in ctx["grants"]))
    if admin:roles.insert(0,"System Administrator")
    if teaching and "Teacher" not in roles:roles.append("Teaching")
    if not roles:roles=["Staff"]
    notice_count=WorkforceNotice.objects.filter(recipient=request.user,acknowledged_at__isnull=True).count() if ctx["workforce_self"] else 0
    name=request.user.get_full_name() or request.user.get_username()
    return {**result,"rf_shell":{"sections":sections,"groups":groups,"active":active[0] if active else None,
        "title":active[0]["label"] if active else "School workspace","roles":roles,"name":name,
        "initials":"".join(x[0].upper() for x in name.split()[:2]),"today":timezone.localdate(),
        "theme":"dark" if request.session.get("rf_theme")=="dark" else "light","notice_count":notice_count,
        "notices":ctx["workforce_self"],"admin":admin,"teaching":teaching}}
