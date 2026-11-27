"""Release-candidate policy, deliberately not changeable by environment flags.

Only an independently reviewed subsequent code release may remove these blockers.
An approval checklist, config file or successful CI run is not authorisation.
"""
VERSION = "5.0.0-rc.4"
CHANNEL = "unsigned synthetic staging release candidate"
OPEN_GATES = (
    ("identity", "Approved identity provider integration, MFA and account lifecycle acceptance"),
    ("integration", "Approved OneSchool transfer and reconciliation, enrolment history and rollback"),
    ("security", "Independent application and infrastructure security review"),
    ("privacy", "School ICT/privacy approval, retention, disclosure and access policy"),
    ("operations", "Operational acceptance of outstanding attendance, movement, workforce and support requirements"),
    ("deployment", "Approved central service, managed HTTPS clients and signed distribution"),
    ("recovery", "Approved encrypted backups, recovery drill and rollback plan"),
    ("capacity", "Full school multi-user, load, concurrency and accessibility acceptance"),
    ("interface", "Approved protected website workflow and visual parity across all authorised staff roles"),
    ("pilot", "Fictional pilot acceptance, staff training and authorised go-live decision"),
)


def assert_school_release():
    if OPEN_GATES:
        raise RuntimeError("RollFlow 5.0 release candidate: school mode blocked. Review the production readiness report; no real school records.")
