"""Static, fictional pilot rehearsal catalogue. Never conveys production authority."""
from .release_policy import VERSION, CHANNEL, OPEN_GATES

# Stable scenario IDs for offline evidence. No personal records, names or secrets.
SCENARIOS = (
    ("P01", "Installation and isolation", "ICT deployment",
     "Verify exact successful CI commit and hashes; install each package on approved isolated equipment. Workstation contains no local server."),
    ("P02", "Individual accounts and scope", "ICT identity / administrator",
     "Create separate fictional accounts; verify intended role and negative direct URL/POST access, revocation and sign-out."),
    ("P03", "Reviewed dated school data", "School data owner",
     "Review synthetic timetable and roster imports; resolve skipped pairs and verify publication coverage before attendance."),
    ("P04", "Teacher attendance and correction", "Teaching lead / attendance officer",
     "Save draft, certify one roll, reject stale or duplicate submission, review correction history and local reconciliation."),
    ("P05", "Movement handover", "Student services / teaching lead",
     "Issue a fictional pass, confirm arrival and release, confirm return; reject unrelated staff and stale transitions."),
    ("P06", "Relief and workforce", "Operations lead",
     "Approve cover and room change, verify effective schedule and private notices; reject conflicts and unverified allocations."),
    ("P07", "Learning support and leadership", "Learning support / leadership",
     "Exercise approved support actions and scoped aggregate reports; verify unrelated identities and export restrictions."),
    ("P08", "Accessibility and staff training", "Pilot facilitator",
     "Exercise keyboard, zoom, mobile, screen reader and dark mode using fictional fixtures; record defects and teach fallback."),
    ("P09", "Concurrent use and capacity", "ICT operations",
     "Agree synthetic cohort size, response/error thresholds and duration before testing; record results, contention and recovery."),
    ("P10", "Backup and isolated recovery", "ICT operations",
     "Stop writers, take a private snapshot including archive/key, restore into new independent state, verify histories and invalidated sessions."),
    ("P11", "Outage and incident rehearsal", "ICT / school operations",
     "Stop new writes on integrity concern, preserve evidence, use approved school fallback procedures and reconcile before resuming."),
    ("P12", "Review and exit decision", "Authorised governance",
     "Review exact release evidence, unresolved defects, training, rollback and all open production gates; no real-data pilot approval inferred."),
)
OWNERS = {
    "identity":"ICT identity owner", "integration":"School data owner",
    "security":"ICT security", "privacy":"School privacy/records owner",
    "operations":"Operational leaders", "deployment":"ICT deployment",
    "recovery":"ICT operations", "capacity":"ICT and pilot lead",
    "interface":"Operational leaders and accessibility reviewer", "pilot":"Authorised governance",
}

def plan():
    """New blank checklist each call; completion is not tracked in the application."""
    return {"version": VERSION, "channel": CHANNEL,
            "purpose":"fictional staging rehearsal only", "production_approved":False,
            "school_startup":"blocked",
            "scenarios":[{"id":key,"title":title,"owner_role":owner,"acceptance":acceptance,
                          "status":"not assessed","evidence_reference":None}
                         for key,title,owner,acceptance in SCENARIOS],
            "gates":[{"id":key,"requirement":requirement,"owner_role":OWNERS[key],"status":"open"}
                     for key,requirement in OPEN_GATES]}
