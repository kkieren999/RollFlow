# RollFlow — persistent development handover

**Last reviewed:** 27 November 2026 (Australia/Brisbane)  
**Project:** kkieren999/RollFlow  
**Goal:** Deliver a secure, school-wide Windows/browser application suitable for an approved Queensland secondary school pilot and eventually live deployment. The current website is the UX reference, not the production data layer.  
**Status:** V4.0 security foundation committed; final validation and outstanding security work remain. No production launch or real school data authorised.

## CURRENT CHECKPOINT — V4.0 security foundation (27 Nov 2026)

**Latest cumulative development branch:** `feature/v4.0-accounts-roles-security`, head `963bf058d32ff67d8173caf69ce7bd96a5631e51`, draft PR #37 https://github.com/kkieren999/RollFlow/pull/37 (base windows-release; includes prior drafts). Do not restart from main, windows-release or V3.9 for subsequent development. Recheck actual branch head before edits. Sections below retain the earlier roadmap/history; this checkpoint supersedes older statements of current phase.

### Verified build state
- V3.9 repair d3940a8: run #304 https://github.com/kkieren999/RollFlow/actions/runs/45892929577 — tests and PostgreSQL/native succeeded; Windows browser passed and artifact upload was running at last inspection. PR run #305 same status. Verify completion and actual artifact before reporting download.
- V4.0 first commit 082e5fec: tests failed on unrelated flaky year-scope assertion: the random CSRF token contained substring Y8, not a leaked table cell. Confirmed exact match in log job 140160972140. Repaired in 963bf058 using exact authorised projection and rendered HTML cells, retaining no-private-staff-code assertion.
- V4.0 second commit 6cbbfbad: standard tests job 140161285080 in run #307 succeeded; PostgreSQL/native in progress at last inspection.
- Latest exact-commit run #309 https://github.com/kkieren999/RollFlow/actions/runs/45893460694 and PR run #310 https://github.com/kkieren999/RollFlow/actions/runs/45893468770 are in progress. Windows package name RollFlow-V4.0.0-Accounts-Roles-Security-Windows-x64-STAGING. No verified V4.0 artifact yet.

### Implemented
- Additive migrations 0016/0017, RoleTemplate and AccessAudit, optional grant start/expiry, source template provenance, temporary publication-bound class metadata scope.
- Administrator can create/archive reviewed immutable template versions, copy explicit permissions into grants, revoke grants, view effective grants and structured before/after audit. Archiving a template does not revoke existing copies. Existing grants retain previous scope.
- Scope union still per capability; expired/not-yet-active grants fail closed. Class grants require expiry, active publication, exact class code, only published class/timetable metadata. Republish invalidates. No roster or marking access.
- Staff self-password change requires current password, validated new password; invalidates other sessions. Existing account admin status/reset/edit paths now recheck locked actor and audit changes; deactivation revokes delegated grants and sessions, reactivation does not restore those grants. Pending accounts blocked from teaching/admin; raw protected Django user/profile/group mutations disabled. Existing legacy teaching and full system admin remain independent.
- Tests in accounts/test_security_foundation.py for template/expiry/forged scopes and admin role labels/direct URLs/POST/CSRF/revocation/reactivation/password/session invalidation/class publication invalidation. Role/action matrix in docs/v4.0-security.md. Windows staging version bumped to 4.0.0.

### First next tasks (in priority order)
1. Check exact V4.0 runs #309/#310 and V3.9 #304/#305. Fix actual failures, verify Windows artifact; update handover with result. Do not proceed as if passing until checked.
2. Complete earlier V3.9 section 2B protected browser E2E, concurrency and restore drill if not already done. Current Windows packaged browser check validates the fictional site, not full protected operational UI.
3. Finish V4.0 security acceptance: exact time-bounded relief lesson roster/attendance authority, including verified relief identity and publication-specific assignment with expiration/cancellation, avoid changing regular teacher's roll ownership without explicit transactional handover; test both actor and lesson scope. Implement actual delegated action-level write/export permissions only for approved real workflows; current capabilities are read/summary and existing teacher/admin actions. Support/confidential records require separate need-to-know rules. Review remaining legacy account/import/automated activation paths and audit retention; ensure concurrent deactivation, login/session revocation and raw admin bypass cannot widen permissions. Add deterministic browser tests for role management and negative access.
4. SSO/MFA depends on school-approved identity provider and setup; document integration design, do not invent provider credentials or claim compliance. Review shared-network login throttling and session policies with ICT. V4.0 is partial and not production-ready.
5. When these gates pass (or explicitly document approved deferred items), proceed to V4.1 school data and OneSchool integration from verified cumulative head. Keep handover current.

## 0. Start here — instructions for the next ChatGPT session

This file is the durable project handover, not a transcript. Read it in full before changing code. The owner wants actual implementation in GitHub, not just suggestions when asking to build a phase.

1. Connect to the GitHub repository and re-check the live branch heads, open pull requests, workflow runs, job logs and artifacts. Facts in this file are a snapshot; current repository evidence takes precedence.
2. Resume the first incomplete task in the CURRENT CHECKPOINT above, then consult the earlier roadmap sections. Do not start an unrelated implementation or restart from an older release just because it is the default branch.
3. Work from the latest cumulative Windows development branch, presently `feature/v4.0-accounts-roles-security`. For a new phase, create a feature branch from the verified cumulative head. Inspect other overlapping branches before merging. Use an expected-head lease when updating a branch.
4. Preserve working OneSchool imports, database schema/history, access boundaries and public website. Prefer incremental migrations and shared UI components; do not discard working code unnecessarily. Do not merge, deploy, delete existing databases, publish real data, or change school infrastructure without explicit approval.
5. Add tests with fictional data. Run/trigger Django checks, migration consistency, all relevant regression tests, PostgreSQL/native smoke, browser checks and Windows packaging. Investigate failed jobs rather than weakening security or suppressing tests. A queued/running build is not a successful build.
6. Create or update a draft PR. Report actual changes, limitations, branch, commit, PR, test outcomes and a verified artifact URL. Never claim an installer is ready unless the exact commit's required jobs passed and the artifact exists.
7. **Before ending each development session, update this file on the stable `development-handover` branch** (even if the work is incomplete). Record exact current branch/head, PRs, CI status, failed checks, decisions, acceptance criteria, remaining tasks and the next concrete action. Keep its stable URL unchanged. If GitHub writes are unavailable, explicitly tell the owner and provide handover text.

Stable handover URL: https://github.com/kkieren999/RollFlow/blob/development-handover/DEVELOPMENT_HANDOVER.md

## 1. Repository map and verified state

| Purpose | Branch / commit as reviewed |
|---|---|
| Public UX reference / GitHub Pages | `main` — `bbb40b56b2d6c70b660ff894d59db8b7cb250298` |
| Previous Windows release branch (unchanged by these phases) | `windows-release` — `6ac9059306f2e77880b94d549005d738cf77eb17` |
| Cumulative V3.7 access work | `feature/v3.7-staff-access` — draft PR #34 |
| Cumulative V3.8 packaging work | `feature/v3.8-windows-rebuild` — draft PR #35 |
| Prior cumulative V3.9 development source | `feature/v3.9-live-foundation` — `d3940a8f51d8db08e2c8d9954c0e9803449c127f`, draft PR #36 |
| Other overlapping shared-core work | `integration/shared-core`, draft PR #33 to main — inspect independently, do not assume merged |

| **Current cumulative development source** | `feature/v4.0-accounts-roles-security` — `963bf058d32ff67d8173caf69ce7bd96a5631e51`, draft PR #37 |

Links:
- Website: https://kkieren999.github.io/RollFlow/
- Current source: https://github.com/kkieren999/RollFlow/tree/feature/v3.9-live-foundation
- Draft PR: https://github.com/kkieren999/RollFlow/pull/36
- Latest V3.9 repair run #304: https://github.com/kkieren999/RollFlow/actions/runs/45892929577 (running when recorded)
- Previous failed V3.9 push run: https://github.com/kkieren999/RollFlow/actions/runs/45892345586
- Same-commit PR run: https://github.com/kkieren999/RollFlow/actions/runs/45892352243
- Last known successful previous Windows release run: https://github.com/kkieren999/RollFlow/actions/runs/45759753362#artifacts (recheck expiration).

PR #36 includes the previous V3.7/V3.8 changes. Do not merge all three independently without inspecting ancestry; avoid duplicate/cherry-pick drift. Public main and previous Windows release have not been updated by these drafts.

### Architecture and mode boundaries

- Django application, PostgreSQL central storage, Waitress loopback WSGI, Windows x64 offline bundle with embedded CPython and PostgreSQL. SQLite only for development tests, not a live school database.
- Protected workspace uses authenticated server-side data; each staff device should connect to an ICT-approved central service in production, not its own isolated school database. Current staging is loopback only.
- Public website is a fictional browser-local simulation. Its 13 public identities and matching demo passwords are not real authentication. Do not load school records in that interface, import localStorage as authoritative data, or expose private API or archive files through Pages.
- `training/` is an exact pinned public snapshot (source commit in `training/SOURCE_COMMIT.txt`). `deployment/sync_training.py --check` verifies it. `index.html` in the Windows root is the legacy shell; do not mistake it for the full website.
- V3.9 native mode sets `ROLLFLOW_PROTECTED_WORKSPACE=1`; unified sign-in goes to `/live/` and teacher route goes to `/live/day/` rather than the fictional fallback.
- V3.9 Start RollFlow.cmd opens the protected workspace menu. Open Training Demo.cmd runs separately on 127.0.0.1:18086. Fresh protected staging uses %LOCALAPPDATA%/RollFlow-V38-Fresh-Staging, web 18087 / DB 55438; existing protected state uses RollFlow-V3641-Staging, web 18085 / DB 55437. Keep old extracted binaries in place for existing database paths; use backup-first upgrade, never First Setup on an existing instance.
- Production security mode requires approved exact hostname, strong secret, PostgreSQL, HTTPS gateway, DEBUG off; do not weaken those settings to make CI green.

## 2. NEXT ACTION — V3.9 release repair and verification (do this first)

**Verified CI result:** previous runs 45892345586 and 45892352243 completed with failure; Windows packaging was skipped. Repair d3940a8 has now been committed and run 45892929577 started. First next action: inspect that exact commit's CI result, then continue section 2B if native validation passes. The standard tests job passed, including 124 Django tests (SQLite). The native PostgreSQL smoke ran all 124 Django tests successfully, then failed in its subsequent shell smoke. Thus V3.9 has no confirmed downloadable Windows artifact.

### 2A. Fix specific native smoke regression

- [x] Inspect `deployment/ci_smoke.py`, native configuration and the failing job log (job 140157794213 in run 45892345586).
- [x] Root cause: after successful authentication, the new smoke uses `c=Client()` then `c.get('/').url`. Django's test client defaults to host `testserver`, which is intentionally not in the native instance's ALLOWED_HOSTS (localhost). Response is HTTP 400, then AttributeError: 'HttpResponse' object has no attribute 'url'.
- [x] Use `Client(HTTP_HOST="localhost")` (or explicit configured local hostname on each request) for that local smoke. Assert status 302 and Location /live/, then HTTP 200 for /live/. Do **not** add testserver or wildcard to deployment ALLOWED_HOSTS, disable host validation, or remove protected-route checks.
- [x] Commit repair on cumulative V3.9 branch: d3940a8f51d8db08e2c8d9954c0e9803449c127f. CI run #304 triggered.
- [ ] Inspect new CI results; do not mark resolved until native smoke passes. If successful, continue section 2B.

### 2B. Verify the actual packaged Windows application

- [ ] V3.8 prior Windows run 45891635934 failed a packaged browser test because principal's menu had 11 entries vs stale expected 10. V3.9 replaced the brittle count with source-vs-package menu signatures in `deployment/windows_workspace_smoke.cjs`; not yet verified because the latest Windows job was skipped.
- [ ] Run actual packaged browser smoke (all 13 public identities, local assets, menu signatures, routes, logout, no unexpected requests or JS errors). If failing, read actual logs and correct test or implementation with evidence; do not bypass.
- [ ] Run protected browser E2E, not just Django test clients: two separate authenticated browser contexts, fictional published lesson + roster, teacher draft/submit, officer summary updates after refresh, no cross-class access. Add this test if absent.
- [ ] Verify Windows fresh setup, existing backup-first upgrade, preserved archive/key, additive migration 0015, restart and restore test. Verify concurrency with two clients, stale revisions and publication change, rather than assuming locks are sufficient.
- [ ] Check lesson eligibility: currently current-day verified allocation only; make sure non-instructional break/duty entries cannot become attendance rolls, future lessons cannot be submitted prematurely, incomplete/ambiguous memberships fail closed, and changes cannot silently misattribute attendance. Define appropriate school policy before expanding.
- [ ] Inspect the protected UI against the public site, identify every missing route/workflow, and document parity gaps. Do not present training modules as implemented protected functionality.
- [ ] Confirm successful exact-commit workflow jobs and artifact name `RollFlow-V3.9.0-Live-Foundation-Windows-x64-STAGING`, link actual artifact or exact successful run. Keep unsigned staging label and fictional-data warning.
- [ ] Update handover with verified status. Only then move to V4.0; if a blocker remains, record it explicitly.

### Implemented but not production approved (V3.9)

- V3.7: named/custom staff role labels, multiple scoped read grants, faculty/year/school scope, admin grant/revoke, published OneSchool class/timetable projections; teaching and full administrator rights remain separate.
- V3.8: full pinned public training interface packaged separately, isolated fresh protected database, explicit safe existing upgrade path.
- V3.9: authenticated shared workspace, role-based links, today's verified dated lesson roster, central AttendanceRoll and AttendanceRevision, P/A/L marks, draft, explicit certification and submit, locked submitted rolls, school-wide summary monitor (explicit grant or full admin), audit events, stale revision and roster-token checks. Two-session Django tests exist.
- Attendance currently requires dated publication, current imported published version, both reviewed roster reports, zero skipped membership pairs, stable student identities and current enrolment. Ambiguous/overlapping lessons rejected. Changes to publication/roster block edits for review. No historical marking, corrections, temporary relief, approved OneSchool attendance transfer, offline queue or operational reporting.
- Protected design is only partial website parity: a shared shell plus existing native templates, not the entire public UI wired to central data. SSO/MFA, secure production installation and ICT approval remain outstanding.

## 3. Next development phase after V3.9 validation — V4.0 Accounts, Roles and Security

Create `feature/v4.0-accounts-roles-security` from the latest validated V3.9 cumulative head (verify actual branch state first). Build in independently testable increments.

### V4.0 implementation backlog (in order)

- [ ] Inventory all protected URLs, views, HTTP methods and data scopes. Create a role/action/scope matrix covering actual server endpoints. Explicitly identify legacy, admin-only, teacher-only, protected and fictional surfaces.
- [ ] Introduce reusable role templates and explicit action-level capabilities (view/create/update/approve/export/administer as appropriate). Scope to whole school, faculty, year, verified assigned class, named student/task/referral where supported. Deny by default. No cross-grant scope borrowing, privilege escalation, implicit role-name access or automatic promotion. Preserve existing grants and teaching independence via additive migration.
- [ ] Implement safe account management: create/activate/deactivate, reset/recover, role assignment/revocation, temporary start/end dates, effective-permissions preview, audit actor/target/before/after. Validate existing staff identity mapping. Disable pending imports and inactive accounts; revocation and expiry apply server-side on subsequent requests, including active sessions. Protect last administrator and prevent unauthorised delegation.
- [ ] Implement role-aware navigation using server-computed permissions, no hidden-menu-only security. Provide a common protected layout using current website design; role-specific data must come from the authenticated server, not demo fixtures. Keep unimplemented modules unavailable.
- [ ] Temporary relief: model explicit time-bounded verified class/lesson assignments; no blanket timetable/attendance access or exposure of unrelated students. Test expiry, cancellation, overlapping assignments and explicit teacher access. Coordinate detailed operational relief workflow with V4.4.
- [ ] Authentication hardening: review login throttling for shared school networks, session lifetime, deactivation/revocation, CSRF, secure cookies, HTTPS, password policy, account recovery and audit. Do not weaken existing controls. Plan school-approved SSO/MFA using documented provider requirements; do not invent identity provider configuration or claim SSO works without a configured approved IdP.
- [ ] Define approved audit retention/access and sensitive record handling. Do not log passwords, tokens, unnecessary student data or raw exports. Add audit views with scoped access and test logs/exports for leakage.
- [ ] Add positive and negative tests for each supported role, direct URL/POST forgery, guessed IDs, cross-faculty/year/class access, multiple-role union, revoked/expired grants, inactive users, session isolation, CSRF, audit consistency and concurrent updates.
- [ ] Test against SQLite and PostgreSQL, protected browser sessions, and fresh/upgrade Windows package. Produce a fictional staging artifact and a documented role matrix. Update this file.

### Proposed role templates (not automatic rights)

System Administrator (configuration/accounts, not automatic teaching), Principal, Deputy Principal, Head of Department, Head of Year / Year Level Coordinator, Business Manager, Administration Officer, Teacher, Relief Teacher, Teacher Aide, Learning Support Teacher, Student Services, Attendance Officer, Guidance Officer, Custom. Exact permissions require school approval; guidance/support records have additional need-to-know restrictions. HOD/leadership may independently teach. Do not silently grant access by job title.

### V4.0 acceptance

- All implemented permissions enforced server-side on read/write/export; negative tests pass.
- Administrators can inspect and safely change roles/scopes/expiry without giving full admin rights.
- Scoped and mixed-role staff see only their approved modules/data, even via direct URLs.
- Account revocation/expiry takes effect, audit trail retained, no demo bypass in protected mode.
- Existing verified teacher and OneSchool import flows still work; migrations and Windows package pass.
- Clearly document SSO/MFA status and remaining ICT dependencies; no production claims.

## 4. Remaining roadmap

| Phase | Deliverables / acceptance |
|---|---|
| V4.1 School data and OneSchool | Reviewed imports, staff/student identities, enrolment/class history, timetables, terms/bell times, reconciliation, validation/rollback, approved OneSchool attendance transfer design. Preserve encrypted private originals; no unapproved API or credential automation. |
| V4.2 Complete live attendance | Period rolls, overdue status, corrections with reasons/authorisation and immutable history, authorised student-level reports, historical rules, reconciliation and approved daily OneSchool transfer, delivery confirmation, concurrent edits and network failure handling. |
| V4.3 Movements and services | Centrally recorded issue/arrival/return, configurable destinations, scoped live out-of-class dashboard, alerts, timelines and audit; no browser-local authoritative passes. |
| V4.4 Workforce, relief, supervision | Availability, absence and cover, relief assignment and expiry, duties, room changes, calendar exceptions, conflict checks, notifications and approvals. |
| V4.5 Classroom and student support | Seating/class lists, observations, referrals, aide tasks, support allocation/follow-ups with assigned-student/need-to-know access and approved retention. |
| V4.6 Leadership reporting | Authorised school/department/year reporting, filters, overdue actions and exports; reconcile numbers and suppress unauthorised student detail. |
| V4.7 Production installer | Signed installer, standard user/managed installation, shortcuts, service/client configuration, secure HTTPS central access, diagnostics, controlled upgrade and backup/restore/rollback. Signing certificate and ICT configuration are external prerequisites. |
| V5.0 Approved production | Independent security/privacy assessment, load/concurrency tests, backup recovery drills, OneSchool procedure compliance, leadership/ICT approvals, fictional staging then approved pilot, training/support, release/change control. |

## 5. Code map and validation commands

- `accounts/models.py`, `accounts/migrations/0014_staff_access_grant.py`, `0015_attendance_foundation.py`: additive role and attendance schema.
- `accounts/permissions.py`, `accounts/school_access.py`, `accounts/school_access_views.py`: teaching authority, grants and scoped views.
- `accounts/views.py`, `accounts/live_views.py`, `accounts/attendance.py`: login, protected shell and attendance workflow.
- `accounts/connected_school.py`, `accounts/dated_school.py`, `accounts/connected_views.py`, `accounts/oneschool_*.py`: verified publication/import/mapping and roster integrity.
- `templates/live_*.html`, `templates/ui_system.html`, `templates/ui_header.html`: protected UI; public design reference main index/styles.
- `accounts/test_live_foundation.py`, `accounts/test_school_access.py`, existing account tests: regression coverage.
- `deployment/native.py`, `deployment/ci_smoke.py`, `deployment/build_windows.py`, `deployment/windows_launchers.py`, `deployment/windows_workspace_smoke.cjs`, `.github/workflows/v3-test.yml`: packaging, native and browser checks.
- Read `docs/v3.7-staff-access.md`, `docs/v3.8-windows-rebuild.md`, `docs/v3.9-live-foundation.md` and `deployment/README.md` on cumulative branch.

Run from a clean checkout with dependencies installed and test settings (not a real data directory):
```
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test accounts
python deployment/sync_training.py --check
python -m unittest deployment.test_training deployment.test_windows_launchers deployment.test_native_permissions -v
node training/tests/teaching-permissions-logic.cjs
node training/tests/calendar-logic.cjs
node training/tests/classroom-management-logic.cjs
node training/tests/room-changes-logic.cjs
```
Use ROLLFLOW_DEBUG=1 for isolated dev checks as appropriate. PostgreSQL CI: `python deployment/ci_smoke.py` on its configured Ubuntu PostgreSQL runner. The Windows job uses vetted embedded runtime archives, native database/upgrade smoke and packaged browser smoke; check actual logs. Keep all artifacts fictional, never include local databases or school files.

## 6. Non-negotiable production gates

- No real student/staff records in public Pages, GitHub, chat, fictional training or unsigned staging packages. No passwords, API keys, private export files or sensitive identifiers in commits, issues, logs or this handover.
- OneSchool remains authoritative for official attendance; verify current Queensland departmental procedure and approved transfer/reconciliation process before real use. No scraping or unapproved automated writes.
- Obtain school/department ICT, privacy and leadership approval and current regulatory/policy verification. Use HTTPS, central access, least privilege, encrypted backups, tested restore, incident response, approved retention and independently reviewed security.
- Do not label a staging build production-ready. Source commits, passing unit tests, successful Windows package, approved pilot and live deployment are different milestones.
- Official references to recheck for current requirements: https://ppr.qed.qld.gov.au/pp/roll-marking-in-state-schools-procedure and https://ppr.qed.qld.gov.au/pp/non-departmental-ict-service-providers-procedure .

## 7. Session log (newest first)

### 27 Nov 2026 — V4.0 security foundation implemented
- See CURRENT CHECKPOINT above. Cumulative branch feature/v4.0-accounts-roles-security, head 963bf058d32ff67d8173caf69ce7bd96a5631e51, draft PR #37. Tests and final Windows package require exact-commit validation. No releases or production deployment.

### 27 Nov 2026 — native hostname repair committed
- Cumulative head: d3940a8f51d8db08e2c8d9954c0e9803449c127f on feature/v3.9-live-foundation, draft PR #36.
- Changed deployment/ci_smoke.py to use Client(HTTP_HOST='localhost'), explicit HTTP 302 and Location checks, then HTTP 200 for /live/. No deployment security settings changed.
- New CI run #304: https://github.com/kkieren999/RollFlow/actions/runs/45892929577. In progress when recorded. No new Windows artifact verified yet.
- Next: inspect native and Windows jobs, fix any remaining failures, complete section 2B before V4.0.

### 27 Nov 2026 — handover created
- Rechecked cumulative branch and exact CI jobs: SQLite and PostgreSQL 124 Django tests passed; native smoke failed on testserver host; Windows skipped. First action is section 2A, not a new feature phase.
- Handover created on dedicated stable branch to avoid modifying public Pages or Windows release. No application code changed in this handover session.
- Owner's goal: launch a complete school-wide Windows application using the current website as design reference; preserve existing school data; continue across new chats using this file.

### Template for every subsequent development session
- Date and phase:
- Current cumulative branch and exact head:
- Changes actually committed (paths, migration, decisions):
- PR URL and state:
- Exact CI runs/jobs and test results (pass/fail/pending):
- Confirmed artifact URL/version or reason absent:
- Known security, UX and data limitations:
- First next task (exact file/action and acceptance):
- Remaining tasks and approval dependencies:
