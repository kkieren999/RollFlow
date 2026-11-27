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
