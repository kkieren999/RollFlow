"""Read-only projections for verified personal teaching allocations.

No historical enrolment reconstruction, no school-wide directory authority.
Today-only attendance writes continue through live_views.mark_roll.
"""
from collections import Counter,defaultdict
from datetime import date,timedelta,time
from django.urls import reverse
from django.utils import timezone
from urllib.parse import urlencode
from .attendance import (publication_ready,own_lessons,lesson_key,lesson_valid,
                         roster_for,AttendanceUnavailable,roll_for,roll_matches,lesson_started)
from .connected_school import personal_codes,visible_slots,date_is_school_day
from .workforce_service import closed,absent,entries,effective_room
from .security_service import eligible_account
from .permissions import can_teach

MIN_DAY=date(1900,1,1)
MAX_DAY=date(2099,12,31)


def bounded_day(raw,today=None):
    today=today or timezone.localdate()
    if not raw:return today
    value=date.fromisoformat(raw)
    if not MIN_DAY<=value<=MAX_DAY:raise ValueError("Date outside supported range.")
    return value


def shift(day,offset):
    return max(MIN_DAY,min(MAX_DAY,day+timedelta(days=offset)))


def allowed(user):
    return eligible_account(user) and can_teach(user)


def dated_ready(pub):
    return publication_ready(pub)


def valid_day(pub,day):
    return bool(pub and date_is_school_day(pub,day))


def safe_slot(row):
    # Never return raw staff codes, other staff records or source JSON.
    return {k:row.get(k,"") for k in ("code","name","period","start","end","room")}


def personal_schedule(pub,user,day,today=None):
    today=today or timezone.localdate()
    result={"day":day,"today":day==today,"past":day<today,"ready":dated_ready(pub),
            "school_day":False,"day_closed":False,"unavailable":False,"linked":False,
            "lessons":[],"duties":[],"items":[],"gaps":[],"issue":""}
    if not allowed(user) or not result["ready"]:
        return result
    codes=personal_codes(pub,user)
    result["linked"]=bool(codes)
    if not codes:
        result["issue"]="Your teaching identity has not been verified against the active publication."
        return result
    result["school_day"]=valid_day(pub,day)
    if not result["school_day"]:return result
    result["day_closed"]=closed(pub,day)
    result["unavailable"]=absent(pub,day,user)
    if result["day_closed"] or result["unavailable"]:return result
    # Past schedules are the original allocation, not evidence of who covered a lesson.
    # No historical roster or roll access is opened by this projection.
    all_rows=visible_slots(pub,day)
    valid=[r for r in all_rows if lesson_valid(r)]
    counts=Counter(lesson_key(r) for r in valid)
    def clear(row):
        return counts[lesson_key(row)]==1 and not any(o is not row and
          (o.get("staff")==row.get("staff") or o["code"]==row["code"]) and
          o["start"]<row["end"] and row["start"]<o["end"] for o in valid)
    raw_own=[r for r in valid if r.get("staff") in codes and clear(r)]
    current_rows=own_lessons(pub,user,day) if day>=today else raw_own
    for row in current_rows:
        item=safe_slot(row)
        item.update(kind="lesson",relief=bool(row.get("relief")) if day>=today else False,
                    status="Published allocation" if day<today else "Scheduled",url="",class_url="",classroom_url="")
        if day==today:
            try:
                students=roster_for(pub,row["code"],day)
                roll=roll_for(day,row)
                if roll and not roll_matches(roll,pub,row,user,students):
                    item["status"]="Review required"
                else:
                    item["status"]="Submitted" if roll and roll.submitted_at else "Draft" if roll else "Not started"
                    params=urlencode({"code":row["code"],"period":row["period"],"start":row["start"]})
                    item["url"]=reverse("live-roll")+"?"+params
                    item["classroom_url"]=reverse("classroom-tools")+"?"+params
                    item["class_url"]=reverse("teacher-class-detail",kwargs={"code":row["code"]})
                    item["started"]=lesson_started(day,row)
                    from .workflow_integration import lesson_links
                    item["movement_url"]=lesson_links(row)["movement"]
            except AttendanceUnavailable:
                item["status"]="Roster review required"
        result["lessons"].append(item)
    if day>=today:
        result["duties"]=[{"kind":"duty","period":"Supervision","start":d.start,"end":d.end,
                           "room":d.location,"name":"Supervision duty","status":"Allocated"}
                          for d in entries(pub,day,"duty").filter(staff=user).order_by("start","pk")]
    # Expose only period timing from the publication, not other staff/class allocations.
    # A gap is not a verified spare: it may be a data issue or an allocation not represented here.
    timing=defaultdict(set)
    for row in all_rows:
        try:
            start,end=row["start"],row["end"]
            if isinstance(start,str) and isinstance(end,str) and len(start)==len(end)==5 and time.fromisoformat(start)<time.fromisoformat(end):
                timing[str(row["period"])].add((start,end))
        except (ValueError,TypeError,KeyError):continue
    if day>=today:
        # Use original allocations too so relief/ambiguity never appears as a free period.
        busy=[(r["start"],r["end"]) for r in valid if r.get("staff") in codes]
        busy.extend((r["start"],r["end"]) for r in result["lessons"]+result["duties"])
        for period,windows in timing.items():
            if len(windows)!=1:continue
            start,end=next(iter(windows))
            if not any(a<end and start<b for a,b in busy):
                result["gaps"].append({"kind":"gap","period":period,"start":start,"end":end,
                                       "name":"No verified personal allocation","status":"Not confirmed free"})
    result["items"]=sorted(result["lessons"]+result["duties"]+result["gaps"],
                           key=lambda x:(x["start"],x["end"],x["kind"],x.get("code","")))
    return result


def directory_classes(pub,user,today=None):
    """Current roster only for verified regular allocations today or in remaining publication.

    Relief authority is strictly today's actual verified lesson, not future cover.
    A past-only allocation does not expose current enrolments.
    """
    today=today or timezone.localdate()
    if not allowed(user) or not dated_ready(pub) or not pub.starts<=today<=pub.ends:
        return {}
    codes=personal_codes(pub,user)
    if not codes:return {}
    own=defaultdict(list)
    # Derive unique unambiguous allocations for current/future dates; no raw IDs in output.
    slots=pub.snapshot.get("slots",[])
    bydate=defaultdict(list)
    calendar=set(pub.snapshot.get("calendar",{}).get("dates",[]))
    for row in slots:
        if lesson_valid(row) and row.get("date") in calendar and today.isoformat()<=row["date"]<=pub.ends.isoformat():
            bydate[row["date"]].append(row)
    for iso,rows in bydate.items():
        try:day=date.fromisoformat(iso)
        except (ValueError,TypeError):continue
        if not valid_day(pub,day):continue
        counts=Counter(lesson_key(r) for r in rows)
        for r in rows:
            if r.get("staff") not in codes or counts[lesson_key(r)]!=1:continue
            if any(o is not r and (o.get("staff")==r.get("staff") or o["code"]==r["code"])
                   and o["start"]<r["end"] and r["start"]<o["end"] for o in rows):continue
            own[r["code"]].append(r)
    for row in own_lessons(pub,user,today):
        if row.get("relief"):own[row["code"]].append(row)
    result={}
    for code,rows in own.items():
        try:students=roster_for(pub,code,today)
        except AttendanceUnavailable:continue
        record=next(c for c in pub.snapshot["classes"] if c["code"]==code)
        result[code]={"code":code,"name":record.get("name",""),"years":record.get("years",[]),
                      "students":students,"count":len(students),
                      "url":reverse("teacher-class-detail",kwargs={"code":code})}
    return result


def student_projection(classes):
    result={}
    for c in classes.values():
        for student in c["students"]:
            if student.pk not in result:result[student.pk]={"student":student,"classes":[]}
            result[student.pk]["classes"].append({"code":c["code"],"name":c["name"],"url":c["url"]})
    return result
