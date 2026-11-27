"""Presentation over exact existing report grants, never a new authority."""
from datetime import timedelta
from urllib.parse import urlencode
from django.urls import reverse
from django.utils import timezone
from .reporting import available, build
from .report_views import pick, parse_dates
from .connected_school import current


def report_link(choice,start=None,end=None):
    query={k:choice[k] for k in ("domain","scope","value")}
    if start is not None:query.update(start=start.isoformat(),end=end.isoformat())
    return reverse("leadership-reports")+"?"+urlencode(query)


def dashboard(user,query=None):
    choices=available(user)
    if not choices:return None
    query=query if query is not None else {}
    choice=pick(choices,query)
    if not choice:return None
    today=timezone.localdate()
    # Default daily operations view, or existing fixed completed support week.
    params={k:query.get(k) for k in ('start','end') if k in query}
    if choice["domain"]!="support" and not any(k in params for k in ("start","end")):
        params.update(start=today.isoformat(),end=today.isoformat())
    start,end=parse_dates(params,choice["domain"])
    pub=current()
    rows,notes=build(pub,choice,start,end)
    metrics=[{"label":label,"value":value} for label,value in rows]
    # No percentage inferred from student counts; this is roll completion only.
    counts=dict(rows)
    expected=counts.get("Scheduled lesson keys",0)
    submitted=counts.get("Verified submitted rolls",0)
    completion=None
    if choice["domain"]=="attendance" and isinstance(expected,int) and expected>0 and 0<=submitted<=expected:
        completion=round(100*submitted/expected,1)
    links=[]
    for c in choices:
        links.append({**c,"query":urlencode({k:c[k] for k in ("domain","scope","value")}),
                      "selected":c==choice})
    return {"choice":choice,"choices":links,"start":start,"end":end,"publication":pub.pk if pub else None,
            "metrics":metrics,"notes":notes,"completion":completion,
            "report_url":report_link(choice,start,end)}


def operational_summary(user,pub=None):
    """Whole-school operational monitors only, distinct from scoped reports.

    No named records, report authority, export access or new writes.
    """
    from .security_service import eligible_account
    from .attendance import can_monitor,publication_ready
    from .attendance_operations import daily_status
    from .connected_school import date_is_school_day
    from .movement_service import authority as movement_authority,visible
    from .workforce_service import authority as workforce_authority,entries,coverage,closed
    if not eligible_account(user):return []
    today=timezone.localdate()
    pub=current() if pub is None else pub
    ready=bool(publication_ready(pub) and date_is_school_day(pub,today))
    sections=[]
    def add(label,route,metrics,note):
        sections.append({"label":label,"url":reverse(route),"metrics":[{"label":k,"value":v} for k,v in metrics],"note":note})
    if can_monitor(user):
        values=[]
        if ready:
            _,summary=daily_status(pub,today)
            values=[("Scheduled lesson keys",summary["expected"]),("Verified submitted rolls",summary["submitted"]),
                    ("Outstanding rolls",summary["outstanding"]),("Data exceptions",summary["exceptions"])]
        add("Attendance Overview","live-monitor",values,"Current reviewed day; not official pupil attendance percentages." if ready else "No source-ready published school day.")
    if movement_authority(user)[1]:
        qs=visible(user).filter(closed_at__isnull=True)
        add("Student Movements","movement-board",[("Open passes",qs.count()),("Overdue passes",qs.filter(due_at__lte=timezone.now()).count())],
            "All dates, including carryover. Recorded events only, not physical location.")
    if workforce_authority(user):
        values=[]
        if ready:
            rows=coverage(pub,today)
            q=entries(pub,today)
            values=[("Recorded full-day unavailability",q.filter(kind="absence").count()),
                    ("Uncovered lessons",sum(not r["covered"] for r in rows)),
                    ("Supervision duties",q.filter(kind="duty").count()),("Room changes",q.filter(kind="room").count())]
        add("Workforce Allocations","workforce-board",values,
            "Approved closure for today." if ready and closed(pub,today) else
            "Current recorded changes, not actual staff availability." if ready else "No source-ready published school day.")
    return sections
