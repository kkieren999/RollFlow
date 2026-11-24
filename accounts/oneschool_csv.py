"""Parse only the timetable schema; never retain source file or MISID."""
import csv
import hashlib
import io
import json
import re
from collections import Counter, defaultdict
from datetime import datetime

HEADER = ["Class_Name","Subject_Name","Subject_Level_Code","Day","Date","Period","Start_Time","End_Time","Staff_Id","Staff_MISID","Staff_Code","Staff_Last_Name","Staff_First_Name","Facility_Code","Facility_Name"]
MAX_BYTES = 20 * 1024 * 1024
MAX_ROWS = 150_000
DAYS = ["Mon","Tue","Wed","Thu","Fri"]

def validate_quoting(text):
    """Reject quotes inside bare fields or characters following a closed quote."""
    mode=0
    at_start=True
    i=0
    while i<len(text):
        c=text[i]
        if mode==1:
            if c=='"':
                if i+1<len(text) and text[i+1]=='"':
                    i+=2
                    continue
                mode=2
        elif c in ",\r\n":
            mode=0
            at_start=True
        elif mode==2:
            raise ValueError("Unexpected character after closing CSV quote.")
        elif c=='"':
            if not at_start:
                raise ValueError("Unexpected quote in unquoted CSV field.")
            mode=1
            at_start=False
        else:
            at_start=False
        i+=1
    if mode==1:
        raise ValueError("Unclosed quoted CSV field.")

def parse_year(value):
    label=value.strip()
    if label.casefold() in {"prep","preparatory","foundation","reception","p","f","k","kindergarten"}:
        return 0
    match=re.fullmatch(r"(?:year\s*)?([0-9]{1,2})",label,re.I)
    if match and int(match.group(1))<=12:
        return int(match.group(1))
    raise ValueError("Invalid year level.")

def parse(raw):
    if not raw or len(raw)>MAX_BYTES:
        raise ValueError("Choose a CSV up to 20 MB.")
    try:
        text=raw.decode("utf-8-sig")
    except UnicodeError:
        raise ValueError("Save the export as UTF-8 CSV.") from None
    validate_quoting(text)
    reader=csv.DictReader(io.StringIO(text,newline=""), strict=True)
    try:
        headings=reader.fieldnames
    except csv.Error:
        raise ValueError("Malformed CSV header.") from None
    if headings != HEADER:
        raise ValueError("The column headings do not match the OneSchool Timetable Export.")
    seen=set()
    days=defaultdict(list)
    classes,staff,rooms,periods=set(),set(),set(),set()
    staff_codes,code_ids=defaultdict(set),defaultdict(set)
    warnings=Counter()
    source_rows=0
    try:
        for number,row in enumerate(reader,2):
            source_rows+=1
            if source_rows>MAX_ROWS:
                raise ValueError("Maximum 150,000 rows per import.")
            if None in row or any(v is None for v in row.values()):
                raise ValueError(f"Incorrect number of columns on row {number}.")
            r={k:v.strip() for k,v in row.items()}
            r["Staff_Id"]=r["Staff_Id"].upper()
            r["Staff_Code"]=r["Staff_Code"].upper()
            if any(len(v)>250 or "\x00" in v for v in r.values()):
                raise ValueError(f"Invalid field on row {number}.")
            try:
                date=datetime.strptime(r["Date"],"%d/%m/%Y").date()
                start=datetime.strptime(r["Start_Time"],"%H:%M").time().strftime("%H:%M")
                end=datetime.strptime(r["End_Time"],"%H:%M").time().strftime("%H:%M")
                year=parse_year(r["Subject_Level_Code"])
                if not 1900<=date.year<=2099 or date.weekday()>4 or r["Day"]!=DAYS[date.weekday()] or start>=end or year not in range(13) or not all(r[k] for k in ("Class_Name","Subject_Name","Period")):
                    raise ValueError()
            except ValueError:
                raise ValueError(f"Invalid required class, year, weekday, date or times on row {number}.") from None
            item=dict(code=r["Class_Name"],subject=r["Subject_Name"],year=year,period=r["Period"],start=start,end=end,staff_id=r["Staff_Id"],staff_code=r["Staff_Code"],room=r["Facility_Code"],room_name=r["Facility_Name"])
            day=date.isoformat()
            key=(day,tuple(item.values()))
            if key in seen:
                warnings["duplicate_rows"]+=1
                continue
            seen.add(key)
            days[day].append(item)
            classes.add(item["code"]); periods.add(item["period"])
            if item["staff_id"]:
                staff.add(item["staff_id"])
                if item["staff_code"]:
                    staff_codes[item["staff_id"]].add(item["staff_code"])
                    code_ids[item["staff_code"]].add(item["staff_id"])
            else:
                warnings["missing_staff"]+=1
            if item["room"]:
                rooms.add(item["room"])
            else:
                warnings["missing_room"]+=1
    except csv.Error:
        raise ValueError("Malformed CSV structure.") from None
    if not days:
        raise ValueError("No lesson allocations found.")
    warnings["staff_id_code_conflicts"]=sum(len(v)>1 for v in staff_codes.values())+sum(len(v)>1 for v in code_ids.values())
    # Flag overlapping allocations for review, including different period labels.
    for rows in days.values():
        for field,label in [("staff_id","staff_overlap"),("room","room_overlap")]:
            groups=defaultdict(list)
            for row in rows:
                if row[field]:
                    groups[row[field]].append(row)
            for group in groups.values():
                latest=""
                for row in sorted(group,key=lambda x:(x["start"],x["end"])):
                    if row["start"]<latest:
                        warnings[label]+=1
                    latest=max(latest,row["end"])
        rows.sort(key=lambda x:(x["start"],x["end"],x["period"],x["year"],x["code"],x["staff_id"],x["room"],x["subject"],x["staff_code"],x["room_name"]))
    days=dict(sorted(days.items()))
    digest=hashlib.sha256(b"rollflow-v344\0"+raw).hexdigest()
    summary=dict(source_rows=source_rows,lessons=len(seen),classes=len(classes),staff=len(staff),rooms=len(rooms),periods=len(periods),days=len(days),first_date=min(days),last_date=max(days),warnings=dict(warnings))
    return days,summary,digest
