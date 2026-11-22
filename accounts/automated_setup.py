"""Local-only extraction of staff PDF setup evidence."""
import hashlib
import io
import json
import re
from collections import Counter, defaultdict
from datetime import time
from pypdf import PdfReader
from .connected_school import DAYS, canonical, source_set, source_file
from .models import OneSchoolLineAllocation, OneSchoolStaffClassReference
from .oneschool_staff_pdf import VERSION, STAFF_CODE

HEADER = re.compile(r"^\s*([A-Z0-9_-]{3,40})\s+-\s+([^,\n]+),\s*([^\n]+)$")
ROW = re.compile(r"^\s*(P[1-4]|ISM|HCG|ASM\s*/|FB[123]|SB[12])\s+")
RANGE = re.compile(r"(?<!\d)(\d{1,2}:\d{2})\s*-\s*(\d{1,2}:\d{2})(?!\d)")

def clock(value):
    h,m=map(int,value.split(":"))
    if 1 <= h <= 6:
        h+=12
    if not 7 <= h <= 18:
        raise ValueError("Outside school-day clock")
    return time(h,m).strftime("%H:%M")

def page_details(layout,plain):
    lines=layout.splitlines()
    first=next((s.strip() for s in plain.splitlines() if s.strip()),"")
    staff=None
    for text in lines[:12]:
        m=HEADER.fullmatch(text)
        if m and m[1]==first and STAFF_CODE.fullmatch(first):
            last,given=m[2].strip(),m[3].strip()
            if 0<len(last)<=100 and 0<len(given)<=100:
                staff={"code":first,"first":given,"last":last}
            break
    heading=next((s for s in lines if all(re.search(r"\b"+d+r"\b",s) for d in DAYS)),None)
    slots={}
    if heading:
        anchors=[re.search(r"\b"+d+r"\b",heading).start() for d in DAYS]
        if anchors!=sorted(set(anchors)):
            return staff,slots
        spacing=min(b-a for a,b in zip(anchors,anchors[1:]))
        if spacing<12:
            return staff,slots
        for text in lines[lines.index(heading)+1:]:
            if text.strip().startswith("Legend:"):
                break
            row=ROW.match(text)
            if not row:
                continue
            label="ASM/EHCG" if row[1].startswith("ASM") else row[1]
            for m in RANGE.finditer(text,row.end()):
                i=min(range(5),key=lambda i:abs(m.start()-anchors[i]-spacing/4))
                if abs(m.start()-anchors[i]-spacing/4)>spacing/2:
                    continue
                try:
                    span=(clock(m[1]),clock(m[2]))
                    if span[0]>=span[1]:
                        continue
                except ValueError:
                    continue
                key=(i+1,label)
                if key in slots and slots[key]!=span:
                    raise ValueError("Conflicting times on a PDF page.")
                slots[key]=span
    return staff,slots

def inspect_pdf_setup(raw,expected_version):
    reader=PdfReader(io.BytesIO(raw),strict=True)
    if reader.is_encrypted or not 1<=len(reader.pages)<=200:
        raise ValueError("Expected a readable staff timetable of 1–200 pages.")
    votes=defaultdict(Counter)
    people={}
    conflicts=set()
    missing_names,missing_grids=[],[]
    titles=set()
    for n,page in enumerate(reader.pages,1):
        plain=page.extract_text() or ""
        v=VERSION.search(plain)
        if not v or v[1]!=str(expected_version):
            raise ValueError("Archived PDF version differs from approved timetable.")
        layout=page.extract_text(extraction_mode="layout") or ""
        staff,slots=page_details(layout,plain)
        if staff:
            code=staff["code"]
            if code in people and people[code]!=staff:
                conflicts.add(code)
            people[code]=staff
        else:
            missing_names.append(n)
        if not all((d,f"P{p}") in slots for d in range(1,6) for p in range(1,5)):
            missing_grids.append(n)
        for key,span in slots.items():
            votes[key][span]+=1
        for line in layout.splitlines()[:5]:
            m=re.fullmatch(r"\s*Staff Timetable\s*-\s*(.+?)\s*",line)
            if m:
                titles.add(m[1][:100])
    for code in conflicts:
        people.pop(code,None)
    periods=[]
    for d in range(1,6):
        for p in range(1,5):
            values=votes.get((d,f"P{p}"),{})
            span=next(iter(values)) if len(values)==1 else ("","")
            periods.append(dict(day=DAYS[d-1],period=p,start=span[0],end=span[1],votes=sum(values.values()),conflict=len(values)>1))
    extras=[dict(day=DAYS[d-1],label=label,options=[dict(start=s,end=e,pages=n) for (s,e),n in sorted(v.items())]) for (d,label),v in sorted(votes.items()) if not label.startswith("P")]
    return dict(people=sorted(people.values(),key=lambda x:x["code"]),periods=periods,extras=extras,missing_names=missing_names,missing_grids=missing_grids,conflicting_codes=sorted(conflicts),pages=len(reader.pages),term_hint=next(iter(titles)) if len(titles)==1 else "")

def setup_candidate():
    batches=source_set()
    pdf=batches["staff_pdf"]
    raw=source_file(pdf)
    result=inspect_pdf_setup(raw,pdf.summary["applied"]["timetable_version_id"])
    counts=Counter()
    evidence=set(OneSchoolStaffClassReference.objects.filter(batch=pdf).values_list("staff_code","class_code"))
    discrepancies=set()
    for code,klass in OneSchoolLineAllocation.objects.filter(batch=batches["tt_alignment"]).values_list("staff_code","class_code"):
        if code:
            counts[canonical(code)]+=1
            if (code,klass) not in evidence:
                discrepancies.add((code,klass))
    result["unrecognised_teaching_codes"]=sorted(set(counts)-{p["code"] for p in result["people"]})
    result["legend_disagreements"]=len(discrepancies)
    for p in result["people"]:
        p["slots"]=counts[p["code"]]
    result["source_batch"]=pdf.pk
    result["digest"]=hashlib.sha256(json.dumps(dict(sources={k:v.pk for k,v in batches.items()},pdf_hash=hashlib.sha256(raw).hexdigest(),result=result),sort_keys=True).encode()).hexdigest()
    return result

def suggested_csv(result):
    return "\n".join(f"{r['day']},{r['period']},{r['start']},{r['end']}" for r in result["periods"])
