"""Scoped student workflow presentation; no additional authority is conferred."""
from collections import defaultdict
from datetime import date,timedelta
from django.utils import timezone
from .movement_service import visible,identity_matches


def movement_day(user,anchor,day,now=None):
    """Only events already visible to this actor, for the anchor's verified identity.

    Group by the recorded lesson interval, not a guessed period grid. An open
    pass can span periods or midnight; do not infer a student's location.
    """
    from .movement_views import projection
    now=now or timezone.now()
    grouped=defaultdict(list)
    # Match original published student identity on each pass; do not join
    # a reused student PK to an older or different identity.
    qs=visible(user).filter(student_id=anchor.student_id,lesson_date=day).order_by("departed_at","pk")
    for m in qs:
        if not identity_matches(m):continue
        row=projection(m,user,now)
        departure=timezone.localtime(m.departed_at)
        clock=departure.strftime("%H:%M")
        if departure.date()!=day or not m.start<=clock<m.end:
            key=("Outside recorded lesson interval","","","")
        else:
            key=(m.period,m.start,m.end,m.class_code)
        row["period"]=m.period
        grouped[key].append(row)
    return [{"period":k[0],"start":k[1],"end":k[2],"code":k[3],"rows":rows}
            for k,rows in sorted(grouped.items(),key=lambda x:(not bool(x[0][1]),x[0][1],x[0][2],x[0][0],x[0][3]))]


def follow_up_date(raw,today=None):
    today=today or timezone.localdate()
    if not raw:
        return today+timedelta(days=7)
    value=date.fromisoformat(raw)
    if not today<=value<=today+timedelta(days=90):
        raise ValueError("Choose a follow-up date from today to 90 days ahead.")
    return value
