"""Bounded, aggregate-only leadership reports. No identifier or record exports."""
from collections import Counter, defaultdict
from datetime import timedelta
from django.utils import timezone
from .school_access import grants_for
from .security_service import eligible_account
from .attendance import publication_ready, lesson_valid, lesson_key
from .attendance_operations import daily_status
from .connected_school import visible_slots,personal_codes,date_is_school_day
from .models import StaffProfile,Student,StudentMovement,WorkforceEntry,SupportTask,SupportReferral
from .movement_service import identity_matches
from .classroom_support import student_matches
from .workforce_service import coverage,closed

DOMAINS={"attendance":"Attendance", "movements":"Student movements",
         "workforce":"Workforce and relief", "support":"Educational support"}
SMALL_CELL=5


def available(user,grants=None):
    if not eligible_account(user):
        return []
    grants=grants_for(user) if grants is None else grants
    result=[]
    for domain,label in DOMAINS.items():
        scopes={(g.scope,g.scope_value) for g in grants if "report_"+domain in g.capabilities
                and g.scope in ("school","faculty","year") and (domain!="support" or g.scope=="school")}
        for scope,value in sorted(scopes):
            export=any(g.scope==scope and g.scope_value==value and "export_"+domain in g.capabilities for g in grants)
            result.append({"domain":domain,"scope":scope,"value":value,"label":label,
                "scope_label":"Whole school" if scope=="school" else (("Faculty: " if scope=="faculty" else "Year: ")+value),
                "export":export})
    return result


class Scope:
    def __init__(self,pub,choice):
        self.pub=pub
        self.kind=choice["scope"]
        self.value=choice["value"]
        self.codes=set()
        self.staff_ids=set()
        self.classes=set()
        if self.kind=="faculty":
            for p in StaffProfile.objects.filter(faculty__iexact=self.value,user__is_active=True).select_related("user"):
                codes=personal_codes(pub,p.user)
                if codes:
                    self.codes.update(codes)
                    self.staff_ids.add(p.user_id)
        if self.kind=="year":
            # All roster members and the reviewed class year metadata must agree.
            students={s.pk:s for s in Student.objects.all().only("pk","student_id","year_level","status")}
            from .connected_school import canonical
            seen=Counter(c.get("code") for c in pub.snapshot.get("classes",[]))
            for c in pub.snapshot.get("classes",[]):
                ids=c.get("students",[])
                years=c.get("years",[])
                if (seen[c.get("code")]==1 and years and all(type(y) is int and y==int(self.value) for y in years)
                    and ids and all(pk in students and students[pk].year_level==int(self.value)
                        and students[pk].status=="active" and canonical(students[pk].student_id)==pub.snapshot.get("student_identity",{}).get(str(pk)) for pk in ids)):
                    self.classes.add(c["code"])

    def keys(self,day):
        slots=defaultdict(list)
        for r in visible_slots(self.pub,day):
            if lesson_valid(r):
                slots[lesson_key(r)].append(r)
        # All matching allocations must satisfy the same selected scope. Never
        # infer faculty from a subject code or borrow a scope from another module.
        return {k for k,rs in slots.items() if self.kind=="school" or
                (self.kind=="faculty" and all(r.get("staff") in self.codes for r in rs)) or
                (self.kind=="year" and k[0] in self.classes)}


def date_range(start,end):
    return [start+timedelta(days=i) for i in range((end-start).days+1)]


def build(pub,choice,start,end,now=None):
    now=now or timezone.localtime()
    domain=choice["domain"]
    if not pub or not pub.active or not publication_ready(pub):
        return [],["No current source-ready dated publication. Reports are unavailable."]
    dates=date_range(start,end)
    days=[d for d in dates if date_is_school_day(pub,d)]
    notes=["Current reviewed publication only. Archived publications and dates outside its calendar are excluded.",
           "Aggregate operational counts, not official OneSchool attendance or confirmed physical location.",
           "Faculty means verified regular teaching allocation, not subject ownership. Year requires a single matching reviewed year and current roster."]
    if len(days)!=len(dates):
        notes.append("Some requested dates are outside the current published calendar; excluded dates are not treated as zero.")
    if not days:
        return [],notes
    if domain=="support" and not (pub.starts<=start and end<=pub.ends):
        return [],notes+["A completed support reporting week must be within the current publication date range."]
    scope=Scope(pub,choice)
    keys={day:scope.keys(day) for day in days}
    metrics=Counter()
    if domain=="attendance":
        for day in days:
            rows,_=daily_status(pub,day,now)
            for r in rows:
                if not r["expected"] or (r["code"],r["period"],r["start"]) not in keys[day]:
                    continue
                metrics["Scheduled lesson keys"]+=1
                if r["status"]=="Submitted":
                    metrics["Verified submitted rolls"]+=1
                    metrics["Current revisions manually reconciled"]+=r["reconciliation"]=="Manually reconciled"
                else:
                    metrics["Outstanding scheduled rolls"]+=1
                    metrics["Overdue scheduled rolls"]+=r["status"].startswith("Overdue")
                    metrics["Scheduled data exceptions"]+="review required" in r["status"]
        labels=["Scheduled lesson keys","Verified submitted rolls","Outstanding scheduled rolls","Overdue scheduled rolls",
                "Scheduled data exceptions","Current revisions manually reconciled"]
        notes.append("Only scheduled valid lesson keys; unmatched rolls and malformed allocations are excluded. No student absence percentages or student-level marks.")
    elif domain=="movements":
        qs=StudentMovement.objects.filter(publication=pub,lesson_date__in=days).select_related("student","publication")
        for m in qs.iterator():
            if (m.class_code,m.period,m.start) not in keys[m.lesson_date] or not identity_matches(m):
                continue
            metrics["Recorded departures"]+=1
            metrics["Currently open from selected dates"]+=m.closed_at is None
            metrics["Currently overdue from selected dates"]+=m.closed_at is None and m.due_at<=now
            metrics["Confirmed returns"]+=m.state=="returned"
            metrics["Administrative closures (return unconfirmed)"]+=m.state=="closed"
        labels=["Recorded departures","Currently open from selected dates","Currently overdue from selected dates",
                "Confirmed returns","Administrative closures (return unconfirmed)"]
        notes.append("Grouped by origin lesson and departure date; current status is not historical as-of status. Identity conflicts excluded. Open passes outside the selected dates remain on the operational board.")
    elif domain=="workforce":
        for day in days:
            for r in coverage(pub,day):
                if (r["code"],str(r["period"]),r["start"]) in keys[day]:
                    metrics["Lessons affected by recorded unavailability"]+=1
                    metrics["Currently valid relief cover"]+=bool(r["covered"])
                    metrics["No currently valid relief cover"]+=not r["covered"]
            qs=WorkforceEntry.objects.filter(publication=pub,day=day,cancelled_at__isnull=True)
            if scope.kind!="year":
                staff=qs if scope.kind=="school" else qs.filter(staff_id__in=scope.staff_ids)
                metrics["Full-day unavailability records"]+=staff.filter(kind="absence").count()
                metrics["Approved supervision duties"]+=staff.filter(kind="duty").count()
            metrics["Approved room changes"]+=sum((e.class_code,e.period,e.start) in keys[day] for e in qs.filter(kind="room"))
            if scope.kind=="school":
                metrics["Approved school closure days"]+=closed(pub,day)
        labels=["Lessons affected by recorded unavailability","Currently valid relief cover","No currently valid relief cover","Approved room changes"]
        if scope.kind!="year":labels+=["Full-day unavailability records","Approved supervision duties"]
        if scope.kind=="school":labels+=["Approved school closure days"]
        notes.append("Coverage reflects currently valid assignments, not proof that past relief teaching occurred. Historical expired cover can appear as no currently valid cover. Year reports omit staff absence and duty counts.")
    else:
        # Fixed completed calendar week, no per-student, class, category, or day
        # breakdown. Suppress small distinct-person populations, even zero.
        distinct=defaultdict(set)
        for model,kind in ((SupportTask,"tasks"),(SupportReferral,"referrals")):
            for record in model.objects.filter(publication=pub,created_at__date__in=days).select_related("student").iterator():
                if not student_matches(record,pub):
                    continue
                label="Students with educational "+kind
                distinct[label].add(record.student_id)
        labels=["Students with educational tasks","Students with educational referrals"]
        notes.append("Fixed completed calendar week only; counts of distinct students, no individual records, states, categories, breakdowns or totals. Cells under five (including zero) suppressed. Not a complete statistical disclosure-control system.")
        return [(label,len(distinct[label]) if len(distinct[label])>=SMALL_CELL else "Suppressed") for label in labels],notes
    return [(label,metrics[label]) for label in labels],notes
