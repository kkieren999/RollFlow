"""Explicitly scoped leadership reports and audited aggregate exports."""
import csv,hashlib,io,json
from datetime import date,timedelta
from django.contrib.auth.models import User
from django.db import transaction
from django.http import HttpResponse,HttpResponseBadRequest,HttpResponseForbidden
from django.shortcuts import redirect
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods
from .attendance_admin_views import lock_sources
from .connected_school import current
from .live_views import page
from .models import StaffAccessGrant
from .reporting import available,build
from .security_service import audit


def parse_dates(query,domain):
    today=timezone.localdate()
    monday=today-timedelta(days=today.weekday())
    default_end=monday-timedelta(days=1) if domain=="support" else today
    end=date.fromisoformat(query.get("end") or default_end.isoformat())
    start=date.fromisoformat(query.get("start") or (end-timedelta(days=6)).isoformat())
    if not 0<=(end-start).days<=6 or end>today or start<today-timedelta(days=365):
        raise ValueError("Choose up to seven days within the past year, ending no later than today.")
    if domain=="support" and (start.weekday()!=0 or (end-start).days!=6 or end>=monday):
        raise ValueError("Educational support requires one completed Monday–Sunday calendar week.")
    return start,end


def snapshot(choice,pub,start,end):
    rows,notes=build(pub,choice,start,end)
    data={"publication":pub.pk if pub else None,"domain":choice["domain"],"scope":choice["scope"],
          "scope_label":choice["scope_label"],"start":start.isoformat(),"end":end.isoformat(),"rows":rows,"notes":notes}
    digest=hashlib.sha256(json.dumps(data,sort_keys=True,ensure_ascii=True,separators=(",",":")).encode()).hexdigest()
    return data,digest


def csv_cell(value):
    value=str(value).replace("\r"," ").replace("\n"," ").replace("\t"," ")
    return "'"+value if value.lstrip().startswith(("=","+","-","@")) else value


def csv_bytes(data):
    buffer=io.StringIO(newline="")
    w=csv.writer(buffer)
    for k in ("domain","scope_label","publication","start","end"):
        w.writerow([k,csv_cell(data[k])])
    w.writerow(["Measure","Count"])
    for label,count in data["rows"]:
        w.writerow([csv_cell(label),csv_cell(count)])
    for note in data["notes"]:w.writerow(["Note",csv_cell(note)])
    return buffer.getvalue().encode("utf-8-sig")


def pdf_bytes(data):
    # Local offline generator; no external service or remote fonts.
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,Table,TableStyle
    from reportlab.lib import colors
    from xml.sax.saxutils import escape
    buffer=io.BytesIO()
    styles=getSampleStyleSheet()
    def para(x,style="BodyText"):return Paragraph(escape(str(x)),styles[style])
    story=[para("RollFlow | Leadership summary","Title"),
           para("FICTIONAL STAGING — not an official OneSchool report"),
           para(data["domain"].title()+" · "+data["scope_label"],"Heading2"),
           para(f'{data["start"]} to {data["end"]} · Publication #{data["publication"]}'),Spacer(1,14)]
    table=Table([[para("Measure"),para("Count")]]+[[para(a),para(b)] for a,b in data["rows"]],colWidths=[360,105],repeatRows=1)
    table.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,0),colors.HexColor("#e7edf2")),("VALIGN",(0,0),(-1,-1),"TOP"),
        ("LINEBELOW",(0,0),(-1,-1),0.4,colors.HexColor("#c9d3db")),("TOPPADDING",(0,0),(-1,-1),8),("BOTTOMPADDING",(0,0),(-1,-1),8)]))
    story.extend([table,Spacer(1,14),para("Interpretation and limits","Heading2")])
    story.extend(para(note) for note in data["notes"])
    SimpleDocTemplate(buffer,pagesize=A4,title="RollFlow leadership aggregate",author="RollFlow").build(story)
    return buffer.getvalue()


def pick(choices,query):
    if not choices:return None
    if not any(k in query for k in ("domain","scope","value")):
        return choices[0]
    return next((c for c in choices if (c["domain"],c["scope"],c["value"])==
                 (query.get("domain"),query.get("scope"),query.get("value",""))),None)


@never_cache
@require_http_methods(["GET","POST"])
def reports(request):
    if not request.user.is_authenticated:return redirect("teacher-login")
    query=request.POST if request.method=="POST" else request.GET
    try:
        with transaction.atomic():
            user=request.user
            if request.method=="POST":
                user=User.objects.select_for_update().get(pk=user.pk)
                list(StaffAccessGrant.objects.select_for_update().filter(user=user).order_by("pk"))
                lock_sources()
            choices=available(user)
            choice=pick(choices,query)
            if not choice:return HttpResponseForbidden("Explicit reporting scope required.")
            start,end=parse_dates(query,choice["domain"])
            pub=current()
            data,digest=snapshot(choice,pub,start,end)
            if request.method=="POST":
                if not choice["export"]:return HttpResponseForbidden("Separate export permission required for this report and scope.")
                if query.get("confirm")!="yes" or query.get("format") not in ("csv","pdf"):
                    return HttpResponseBadRequest("Confirm the selected aggregate export.")
                if not data["rows"] or query.get("digest")!=digest:
                    return HttpResponse("Report changed or sources not ready. Reload and review.",status=409)
                # Recheck expiry before export. Exact scope and module required.
                if not any(c==choice for c in available(user)):
                    return HttpResponseForbidden("Reporting access changed.")
                fmt=query["format"]
                raw=csv_bytes(data) if fmt=="csv" else pdf_bytes(data)
                audit(user,"leadership_report_export",after={"domain":choice["domain"],"scope":choice["scope"],"publication":data["publication"],
                    "start":data["start"],"end":data["end"],"format":fmt,"digest":digest})
                response=HttpResponse(raw,content_type="text/csv; charset=utf-8" if fmt=="csv" else "application/pdf")
                response["Content-Disposition"]=f'attachment; filename="RollFlow-{choice["domain"]}-aggregate-{end.isoformat()}.{fmt}"'
                response["Cache-Control"]="no-store"
                return response
    except ValueError as exc:
        return HttpResponseBadRequest(str(exc))
    from urllib.parse import urlencode
    for c in choices:c["query"]=urlencode({k:c[k] for k in ("domain","scope","value")})
    return page(request,"leadership_reports.html",choices=choices,choice=choice,data=data,digest=digest,start=start,end=end)
