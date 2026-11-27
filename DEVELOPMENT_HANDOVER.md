# RollFlow — persistent development handover

**Last reviewed:** 27 November 2026 (Australia/Brisbane)  
**Project:** kkieren999/RollFlow  
**Goal:** Deliver a secure, school-wide Windows/browser application suitable for an approved Queensland secondary school pilot and eventually live deployment. The current website is the UX reference, not the production data layer.  
**Status:** V5.0 RC1 production launch candidate committed; production startup blocked, validation and approvals remain. No production launch or real school data authorised.

## CURRENT CHECKPOINT — V5.0 RC1 production launch preparation (27 Nov 2026)

**Latest cumulative branch:** `feature/v5.0-production-launch-candidate`, head `d8c7811955faa7ddb68217a9441a42e35925c18b`, draft PR #45 https://github.com/kkieren999/RollFlow/pull/45 (base windows-release). Verify actual head before edits. This supersedes all prior checkpoints.

### Windows readiness exit-code repair (27 Nov 2026)
- Prior RC1 head ba9f6de7, run #341 https://github.com/kkieren999/RollFlow/actions/runs/45932755807: all application, PostgreSQL/native, Windows installer compilation and execution, installed schema, snapshot/archive restoration, fictional website and protected multi-session browser tests passed. Final readiness evidence step failed because its expected exit code 2 propagated to the PowerShell/Actions step. Both artifact uploads skipped; no verified RC installer available from #341.
- New head `d8c7811955faa7ddb68217a9441a42e35925c18b`: Windows CI invokes the unchanged readiness CLI through a Python subprocess, requires exact child exit code 2 and returns 0 to CI only on that expected result. Any other code fails; production launch hold, manifest validation, tests and artifact gates remain intact. Run #343 https://github.com/kkieren999/RollFlow/actions/runs/45942735166 in_progress at inspection. Check latest run and actual artifact IDs before providing downloads. No deployment authorised.

### Windows browser CI repair (27 Nov 2026)
- RC1 prior head `49fb1e1a` runs #339/#340 failed Windows protected multi-session browser test with MODULE_NOT_FOUND playwright-core. Application and PostgreSQL/native jobs in #339 passed. The preceding Chrome step installed Playwright in checkout and set NODE_PATH only in its own PowerShell process; subsequent installed-app step lacked it. RollFlow server and fixture started; this does not establish protected browser acceptance.
- Fixed cumulative RC1 head `ba9f6de79710a371cf81c9e85979b6c687257c55`: explicitly set NODE_PATH in protected browser step to checkout node_modules, verify package exists and Node resolution from installed script before starting test. No test removed or bypassed, no runtime dependency bundled. New run #342 https://github.com/kkieren999/RollFlow/actions/runs/45932761350 in_progress at inspection. No installer verified yet. Recheck latest CI and fix remaining failures before distribution.

### Build status (exact evidence)
- V4.6 repaired head 7ef5dddf9639b90473d1c0ce9bfc4d2c9cac6ca4 run #333 https://github.com/kkieren999/RollFlow/actions/runs/45930453060: all jobs passed; verified artifact 15168621893 https://github.com/kkieren999/RollFlow/actions/runs/45930453060/artifacts/15168621893 expires 11 Dec 2026 02:52 UTC; recheck before download.
- V4.7 exact latest head a511ec7d #336 https://github.com/kkieren999/RollFlow/actions/runs/45930736471 and #337 https://github.com/kkieren999/RollFlow/actions/runs/45930752794: tests and PostgreSQL/native including isolated restore passed; Windows compiling/testing installers at last inspection. Do not claim final installer verified before all jobs and artifacts pass.
- V5.0 RC1 initial commit 690f61736a7f40130b9371cc678808712d5b1158 #338 https://github.com/kkieren999/RollFlow/actions/runs/45931047404; latest exact commit 49fb1e1a #339 https://github.com/kkieren999/RollFlow/actions/runs/45931110509 tests and PostgreSQL/native running. PR #45 opened; inspect exact head PR runs. Expected V5.0 artifacts RollFlow-V5.0.0-rc.1-Windows-Installers-x64-STAGING and RollFlow-V5.0.0-rc.1-Portable-Windows-x64-STAGING; no verified RC installer yet.
- No merge, signing, production release or deployment. No real school records or departmental credentials authorised.

### Implemented
- Version 5.0.0-rc.1 unsigned synthetic staging, cumulative modules retained, no schema migration. rollflow/release_policy.py fixed OPEN_GATES, school native initialization/start/management and standard WSGI school/live-timetable startup blocked. Not an environment toggle or a self-certified checklist. Ordinary staging still supported. No claim that runtime guards stop someone modifying source or using a different server entry point.
- deployment/release_readiness.py CLI, --json and --bundle checks exact candidate version/commit format and SHA256 manifest; --require-production exits 2 while blocked. Local Windows Production Readiness shortcut and CI-generated PRODUCTION-READINESS.json after successful installed browser checks. Manifest establishes integrity only, not publisher authenticity or independent approval.
- ProtectedSessionMiddleware globally checks eligible authenticated accounts in protected workspace and flushes denied sessions; private/no-store headers on authenticated protected responses. Inherits existing local account access controls; no approved SSO/MFA implementation.
- Native exclusive cooperative state lock, stale lock investigation; failed recovery/upgrade guards retained; isolated staging restore checks allowed snapshot entries, archive/key presence and PGDMP magic before initialization. Old binaries/direct processes do not obey the new lock; ICT must stop and retire old code. No automatic rollback to old schema.
- New tests: deployment/test_release_readiness.py, accounts/test_release_concurrency.py (PostgreSQL TransactionTestCase simultaneous certified submissions, one success/one conflict/one revision), accounts/test_protected_session.py. CI checks actual WSGI denial with valid-looking school settings, inherits V4.7 installed Chrome, archive restore and installer smoke. Latest tests pending. No full school capacity claim.
- docs/v5.0-release-candidate.md: nine open gate categories, evidence/approval owner matrix, fictional rollout, incident/recovery and pilot plan. All approvals OPEN.

### Next actions — no automatic launch
1. Verify repaired head d8c78119 and exact PR head and V4.7 #336/#337. Repair actual failing tests/installer compile/restore/browser checks and any package metadata/manifest issues, verify exact artifacts and expiration, update this file. V5.0 RC1 is not a release until verified. Never weaken tests or startup hold to pass.
2. Close outstanding engineering requirements in subsequent cumulative RCs: approved provider selection/registration and actual SSO/MFA integration with immutable identity binding and revocation; authorised OneSchool transfer (local manual reconciliation not delivery), enrolment history and rollback; historical attendance/correction, movement handover, partial-day/recurring relief, assigned confidential support policy, delegated actions and reporting privacy/history; centrally managed client configuration, service lifecycle and monitoring, signing/timestamping, controlled updates; whole-school protected workflow E2E, real concurrency/load/accessibility/outage testing, dependency/security assessment, encrypted production backup/recovery drill. See previous checkpoints and docs for details.
3. Obtain independent security review, school ICT/data/privacy/records approval, operational sign-off, approved provider and integration credentials via private infrastructure, signed distribution and verified recovery, fictional pilot acceptance and explicit exact-release go-live decision. Do not store private evidence or secrets in public GitHub. No real data until authorised. The fixed startup hold can only be removed in a later independently reviewed release after evidence for all gates. Do not edit OPEN_GATES just to launch.
4. Continue with V5.0 RC2 validation and production acceptance rather than declaring an invented V5.1 or an unapproved live launch. Preserve public fictional website and earlier staging releases. Update this same handover file before ending every development session.

## PREVIOUS CHECKPOINT — V4.7 Windows installation and recovery (27 Nov 2026)

**Latest cumulative branch:** `feature/v4.7-windows-installer`, head `a511ec7dea58bdf6108cb62bbc07ae7a433698d4`, draft PR #44 https://github.com/kkieren999/RollFlow/pull/44 (base windows-release). Verify actual head before changes. This supersedes all earlier checkpoints.

### Build status
- V4.5 exact commit 4b034863 #328 passed all jobs; artifact 15154945055 https://github.com/kkieren999/RollFlow/actions/runs/45896510104/artifacts/15154945055 (expires 10 Dec 2026 UTC; recheck).
- V4.6 #331/#332 failed six reporting tests with TypeError StaffAccessGrant object is not callable: LiveFoundationTests.setUp assigns self.grant, shadowing ReportingTests.grant. Renamed test helper to report_grant in 7ef5dddf9639b90473d1c0ce9bfc4d2c9cac6ca4 on feature/v4.6-leadership-reporting; all 164 application tests and PostgreSQL/native jobs passed in repaired #333 https://github.com/kkieren999/RollFlow/actions/runs/45930453060 and #334 https://github.com/kkieren999/RollFlow/actions/runs/45930458695; Windows pending at inspection. V4.7 inherits repair.
- V4.7 initial commit 70830e49 #335 https://github.com/kkieren999/RollFlow/actions/runs/45930631258 standard tests passed; PostgreSQL/native running. Latest exact commit a511ec7d push #336 https://github.com/kkieren999/RollFlow/actions/runs/45930736471 running; draft PR #44 triggered, check exact head PR run. No V4.7 setup file or Windows artifact verified yet.
- Expected artifact names RollFlow-V4.7.0-Windows-Installers-x64-STAGING (two setup EXEs and .sha256 files), RollFlow-V4.7.0-Portable-Windows-x64-STAGING. No signing credentials, no production deployment, no real records or merge authorised.

### Implemented
- deployment/installer.iss: Inno Setup 6 per-user x64 versioned installation wizard for full LocalLab and separate lightweight Workstation. Start menu, optional desktop shortcut; no automatic setup, start, service registration or migration; no same-version overwrite or installing over a private instance. LocalLab deliberately has no unattended uninstaller: old PostgreSQL runtime paths may be referenced by existing instances; manual ICT retirement. Workstation uninstaller preserves URL-only preference. Full staging runtime includes fictional training and protected local DB as separate modes.
- deployment/workstation.py: approved DNS HTTPS origin only, no URL credentials, paths, queries or custom ports; explicit confirmation, local URL-only configuration, default browser sign-in and certificate-checked diagnostic (no redirect following or TLS bypass). No DB or app server in client package. User-configurable URL, not ICT-enforced policy; approved central server DNS/TLS, proxy/firewall, service account, endpoint deployment and service supervision remain ICT tasks.
- deployment/bundle_integrity.py: SHA256 manifest generation and strict verification, path traversal and duplicate guards. Detects corruption, not publisher authenticity. Setup binaries have checksum files; unsigned staging. Actual Authenticode signing/timestamping requires approved credentials and process. No automatic update channel; versioned side-by-side controlled manual updates, retain old runtime.
- deployment/recovery.py, native.py: stopped private snapshot of DB dump, encrypted OneSchool archive and archive key, restrictive ACL, manifest and pg_restore listing; upgrade seals snapshot before migration, failed migration guard blocks subsequent new-code start/manage, no automatic downgrade. restore-staging creates new independent state and ports, restores verified synthetic snapshot, migrates and clears sessions; original untouched. Diagnostics omit secrets and logs. Production recovery, encrypted offsite retention, independent approval still outstanding.
- CI builds both setup EXEs, installs silently only on disposable runner, verifies installed manifests and lightweight client separation, runs previous native checks using installed full app, restores fictional data and encrypted archive, generates protected browser fixture in restored state only, tests three independent browser contexts and real sign-in, roster isolation, locked attendance and monitor summary. Existing training Chrome checks retained. Linux native CI adds isolated restore. Unit tests deployment/test_installer.py. These gates are committed, not yet validated on latest head.
- docs/v4.7-installer.md, deployment/README.md. Windows version 4.7.0 staging, no application schema changes.

### Next actions (strict order)
1. Verify exact #336 and PR runs and repaired V4.6 #333/#334. Repair actual failures in installer/compiler, manifest, restore, fixture/browser or preceding tests, without weakening security. Confirm setup artifacts, actual filenames, hashes, expiry, commit, and tested installation. Record final evidence here. Use no older failing head.
2. Complete V4.7 acceptance: real controlled Windows deployment pilot on approved test infrastructure; approved Authenticode signing/timestamping, managed/pinned server configuration and approved TLS proxy/DNS/firewall, service lifecycle/account and monitoring, controlled release/update and verified rollback plan (do not run old app against migrated DB), approved production backup/restore and retention/RPO/RTO, full protected workflow browser/concurrency/performance and recovery tests. Existing CI only narrow synthetic tests; no school records.
3. V5.0 Production Launch preparation: inventory and finish unresolved prior phase gaps; school ICT/privacy approval, independent security review, approved identity provider SSO/MFA, authorised OneSchool report/transfer method, safe enrolment/rollback and historical attendance/reconciliation, operational policy for movement and confidential support, authorised delegated actions, reporting privacy review, data retention, load/recovery drills, school staff training, pilot and support plan. Do not deploy or claim production approval without explicit evidence. Work may produce readiness checklist and release candidate but actual launch requires approvals and signing. Continue cumulative branch, keep public fictional website unchanged, update this file each session.

## PREVIOUS CHECKPOINT — V4.6 leadership dashboards and reporting (27 Nov 2026)

**Latest cumulative branch:** `feature/v4.6-leadership-reporting`, head `1926ef6704134ac734408b67b9d3567525f0c197`, draft PR #43 https://github.com/kkieren999/RollFlow/pull/43 (base windows-release). Verify actual branch head before edits. This supersedes prior checkpoints.

### Build status
- Repaired V4.4 exact commit 49750926, run #326 https://github.com/kkieren999/RollFlow/actions/runs/45896278993: all jobs passed.
- V4.5 exact commit 4b034863: #328 https://github.com/kkieren999/RollFlow/actions/runs/45896510104 and #329 both passed application, PostgreSQL/native and Windows packaging. Verified V4.5 artifact 15154945055 https://github.com/kkieren999/RollFlow/actions/runs/45896510104/artifacts/15154945055 (expires 10 Dec 2026 21:17 UTC; recheck).
- V4.6 first commit a8e0716c run #330 https://github.com/kkieren999/RollFlow/actions/runs/45928489042; latest exact commit 1926ef67 push #331 https://github.com/kkieren999/RollFlow/actions/runs/45928543300 and PR #332 https://github.com/kkieren999/RollFlow/actions/runs/45928555862: all application/PostgreSQL jobs in progress at inspection. Windows artifact expected RollFlow-V4.6.0-Leadership-Reporting-Windows-x64-STAGING; not verified.
- No merge, production deployment or real data authorised.

### Implemented
- Protected /live/reports/ with exact module and scope selection (school, faculty, year), dedicated report-only workspace entry. Explicit report_attendance/report_movements/report_workforce and matching export_* grants. Faculty based on currently verified original teaching allocation, year only single matching class year and current roster identity/year. No automatic role or system administrator bypass. No cross-domain or cross-scope borrowing. No changes to existing grants.
- Attendance scheduled unique valid lesson keys, verified submissions, outstanding/overdue, exceptions and latest manual reconciliation. Movement departure-date cohort and current state counts; no inferred physical location. Workforce current cover validity, duties, approved room changes/closures, absence counts omitted from year reports. No official OneSchool percentages, historical reconstruction or identifier exports. Current reviewed source-ready publication only, seven-day range within past year.
- Support report/export school-only, completed Monday–Sunday week within current publication, distinct student counts, suppress cells under 5 including zero, no states/categories/student-level breakdown or totals. Basic disclosure minimisation, not approved disclosure-control policy.
- Separate exact-domain/scope export permission, CSRF POST, confirmation, recomputed payload digest, expiry recheck, audit domain/scope/date/publication/format/digest. CSV formula protection and offline ReportLab PDF (requirements update). No schema migration. Version 4.6.0 staging; native Windows smoke actually generates a small PDF.
- Code accounts/reporting.py, accounts/report_views.py, templates/leadership_reports.html, docs/v4.6-reporting.md. Six regression tests accounts/test_reporting.py for exact scope, mixed years, export digest/expiry/CSRF, valid PDF, CSV, attendance changes, movements/workforce scope, support suppression. Final validation pending.

### Next actions
1. Verify exact #331/#332 and repair actual failures; validate Windows artifact and expiry, update this file. No claim of passing until exact head tested.
2. Complete V4.6 acceptance: approved statistical disclosure/retention/export rules, audit and performance/load, historical publications and true as-of snapshots, meaningful combined dashboards, longer-range analytics and scheduled exports if authorised. No raw sensitive student data. Date-limited current-publication reports are not official OneSchool reports.
3. V4.7 Production Windows installer: review current native offline staging package and deployment docs. Build robust signed-installer-ready distribution, upgrade/rollback and central-server/client configuration, approved TLS and host validation, service lifecycle, shortcuts, secure diagnostics, versioned backups and tested restore, integrity verification and controlled update channel. Never embed real secrets, school data, or invent signing credentials; unsigned staging stays explicitly labelled. No production install or public release without explicit approval. Maintain existing training/fictional separation and data preservation. Add genuine protected multi-user browser tests to Windows gate (current fictional website smoke alone is insufficient).
4. V5.0 launch remains gated on independent security review, approved SSO/MFA/OneSchool process and school ICT/privacy approval, full load/concurrency and restore drills, operational acceptance of unfinished V4.0–V4.6 features. Do not bypass gates. Update this handover before finishing each session.

## PREVIOUS CHECKPOINT — V4.5 classroom and student support (27 Nov 2026)

**Latest cumulative branch:** `feature/v4.5-classroom-student-support`, head `4b0348637e54617723ff77f3be965e6340f5bb8e`, draft PR #42 https://github.com/kkieren999/RollFlow/pull/42 (base windows-release, cumulative phases). Recheck actual head before editing. This supersedes earlier checkpoints.

### Build status
- V4.3 all jobs passed (#320), verified artifact 15153412195, expires 10 Dec 2026 UTC; recheck availability.
- V4.4 previous exact commit 9284383e #323/#324 failed on two tests calling a missing WorkforceTests.payload helper (AttributeError); repair commit 49750926 on workforce branch reuses LiveFoundationTests.payload. Repaired PR run #326 https://github.com/kkieren999/RollFlow/actions/runs/45896278993 passed application and PostgreSQL/native; Windows running at inspection. Push #325 https://github.com/kkieren999/RollFlow/actions/runs/45896267894 also requires final check. Do not use prior failing head. V4.5 inherits repair.
- V4.5 initial implementation 54ac1db4 run #327 https://github.com/kkieren999/RollFlow/actions/runs/45896443732; latest exact commit 4b034863 push #328 https://github.com/kkieren999/RollFlow/actions/runs/45896510104 tests in progress at inspection. Draft PR #42 triggered; check exact head runs. Windows artifact expected RollFlow-V4.5.0-Classroom-Student-Support-Windows-x64-STAGING; not verified yet.
- No merge, deployment, production use or real student data authorised.

### Implemented
- Migration 0022 ClassroomPlan, ClassroomObservation, SupportTask, SupportReferral. Teacher-owned publication-bound numbered seating (1–200), unique assigned seats, revision checks, numbered occupied tiles; private structured learning observations and withdrawal. Classroom /live/classroom/ linked from My day and roll. Exact verified regular lesson and roster required; relief sees current roster only, no persistent writing/observations.
- Support board /live/support/ and scoped POST state transitions. Explicit school capabilities support_task (named task recipient only), support_referral (named assigned reviewer only), support_coordinator (school-wide minimal educational coordination). No automatic administrator or role-title access. Teacher requester must retain current regular lesson allocation. Revocation/expiry, publication/identity/enrolment validation, CSRF, state revision checks; archived publication fails closed. No automatic transfer.
- Educational task assign/accept/complete/cancel; referral request/assign or reassign/review/close/withdraw; structured categories only, seven-day follow-up default. No medical, safeguarding, confidential narrative or emergency workflow. Audited action metadata; no narrative. No external notification or export.
- Code accounts/classroom_support.py, accounts/classroom_views.py, templates/classroom_tools.html, templates/support_board.html, tests accounts/test_classroom_support.py (seating/forgery, observation withdrawal, named scope/role/revocation/expiry, state, relief, stale identity, CSRF); docs/v4.5-classroom-support.md. Windows version 4.5.0.

### Next actions
1. Check exact latest V4.5 #328 and PR CI, and repaired V4.4 #325/#326; repair actual errors, verify artifacts and expiry, update handover. Do not equate initial tests or implementation with verified build.
2. Finish V4.5 acceptance: policy-approved retention, finer student/task assignment scope and expiry, historical handover after republish, coordinator read/write audit review, accessibility and configurable seating layout, individual learning plan documents, approved confidential casework separation and urgent procedures, protected multi-user tests/concurrency/load/backup recovery. Seven-day follow-up is an unapproved staging default. No live data.
3. Next major phase V4.6 Leadership Dashboards and Reporting: role-specific school/faculty/year scoped aggregates for attendance, movements, workforce and educational support; avoid cross-module scope borrowing, student-level support detail or inferred absence/location. Explicit reporting capability, approved CSV/PDF exports, suppression/minimisation as appropriate, date filters, source/revision validity, audit and negative access tests. Preserve prior data and functionality.
4. Prior V4.0–V4.4 gates remain outstanding including approved SSO/MFA, delegated action permissions, approved OneSchool transfer and rollback/enrolment history, historical attendance and movement handover policy, full protected multi-session browser E2E, concurrency/load, backup restore, ICT/privacy approval. No production release.

## PREVIOUS CHECKPOINT — V4.4 workforce, relief and supervision (27 Nov 2026)

**Latest cumulative branch:** `feature/v4.4-workforce-relief-supervision`, head `9284383eae9ea3b6148174cea509f5c41e1a4e28`, draft PR #41 https://github.com/kkieren999/RollFlow/pull/41 (base windows-release; cumulative previous phases). Check actual head before edits. This supersedes earlier checkpoints.

### Build status
- V4.2 exact commit 19b992e8 run #317 https://github.com/kkieren999/RollFlow/actions/runs/45894329046: all jobs passed; verified artifact 15153217073 https://github.com/kkieren999/RollFlow/actions/runs/45894329046/artifacts/15153217073.
- V4.3 exact commit 456a481e run #320 https://github.com/kkieren999/RollFlow/actions/runs/45894760678: all jobs passed; verified artifact 15153412195 https://github.com/kkieren999/RollFlow/actions/runs/45894760678/artifacts/15153412195. Both artifacts expire 10 Dec 2026 UTC; recheck before download.
- V4.4 initial commit f32e113e run #322 https://github.com/kkieren999/RollFlow/actions/runs/45895339892 standard tests passed, PostgreSQL/native running. Latest exact commit 9284383e push #323 https://github.com/kkieren999/RollFlow/actions/runs/45895406331 and PR #324 https://github.com/kkieren999/RollFlow/actions/runs/45895420628: checks in progress. Windows artifact RollFlow-V4.4.0-Workforce-Relief-Supervision-Windows-x64-STAGING not verified yet.
- No production deployment, merge, or real school records authorised.

### Implemented
- Migration 0021 WorkforceEntry and WorkforceNotice. Date-specific administrator-approved full-day unavailability, supervision duties, room changes and school day closure overlay on current reviewed dated publication, preserving original data. Cancel rather than delete, audit, no personal/medical absence reasons. Room conflicts and return-to-original-room checks, duty/relief conflicts, closure blocks with attendance/movements or existing operational allocations. Prior publication entries are historical; republish requires review.
- Protected /live/workforce/ board, explicit school-wide read-only workforce_monitor grant, admin-only create/cancel. Unavailable teachers' affected lessons and relief coverage. /live/workforce/mine/ personal duties/absence/relief and private inbox, CSRF-protected acknowledgement limited to recipient. Acknowledgement is not external delivery confirmation.
- Existing ReliefAttendanceAssignment now supports today or future selected date up to 180 days, no overlapping duties/lessons/relief, no assignment to unavailable staff, no automatic reassignment/cancellation if recorded roll/movement. Exact relief access reuses current verified publication binding and expires at end of assigned day. No historical attendance changes or new user promotion.
- own_lessons suppresses closed days/unavailable teachers and projects approved effective room, applies to protected daily attendance and movement issue. Attendance monitor flags uncovered absence and closure. Existing movement and roll history remain unchanged. Original allocations conservatively count as busy.
- Tests accounts/test_workforce.py: absence cover, duties/rooms, cancellation, closure and records, future relief, scope isolation, private notices, CSRF. Docs docs/v4.4-workforce.md. Windows version 4.4.0.

### Next actions
1. Verify exact #323/#324 CI, fix actual failures, verify artifact, update handover. Do not label V4.4 validated from initial tests. Protected multi-user browser test, load/concurrency and recovery gates still needed.
2. Finish workforce acceptance: partial-day and recurring availability/duties, multi-campus constraints, bulk allocation and optimisation, staff request/approval workflow, external alerts, authorised delegated workforce writes, notice delivery/ack review, republish reconciliation and uniform room overlays across remaining legacy timetable displays. Approved school policy for closures and duty coverage; school calendar overlay does not update OneSchool. No payroll or leave system.
3. Next major phase V4.5 Classroom and Student Support: build teacher classroom management, authorised roster/class seating and observations, differentiated learning support/aide allocation, referrals and follow-ups with strict assigned-student and need-to-know scopes; no medical/guidance case details in general notes or movement logs. Establish approved retention/access and audit policies, validate direct URL/write/role boundaries and privacy. Preserve existing attendance/movements/workforce. Use synthetic data only.
4. Earlier V4.0–V4.3 production gates still outstanding: approved SSO/MFA, delegated actions, approved OneSchool transfer, full protected multi-user and concurrency testing, backup restore and ICT/privacy approvals. Never represent staging artifact as live deployment.

## PREVIOUS CHECKPOINT — V4.3 student movements and services (27 Nov 2026)

**Latest cumulative branch:** `feature/v4.3-student-movements`, head `456a481e0d919711139bb6dde2a918ab281b90d3`, draft PR #40 https://github.com/kkieren999/RollFlow/pull/40 (base windows-release; includes previous phases). Verify actual head before changes. This supersedes previous checkpoints.

### Build status
- V4.1 exact commit a664b900 run #314 https://github.com/kkieren999/RollFlow/actions/runs/45893959902: all jobs passed and verified artifact 15151984859 https://github.com/kkieren999/RollFlow/actions/runs/45893959902/artifacts/15151984859 (expires 10 Dec 2026 UTC, recheck).
- V4.2 exact commit 19b992e8 run #317 https://github.com/kkieren999/RollFlow/actions/runs/45894329046: tests and PostgreSQL/native passed; Windows Chrome step running at inspection. PR #318 also passed tests and PostgreSQL/native at earlier inspection; recheck packaging.
- V4.3 initial commit 0974ffc2 run #319 https://github.com/kkieren999/RollFlow/actions/runs/45894680285 and latest commit 456a481e run #320 https://github.com/kkieren999/RollFlow/actions/runs/45894760678: application/PostgreSQL checks running. Final Windows artifact name RollFlow-V4.3.0-Student-Movements-Windows-x64-STAGING. No verified V4.3 artifact yet.
- No production launch, merge or use of real school records authorised.

### Implemented
- Additive migration 0020 MovementDestination, StudentMovement, MovementEvent; unique open pass per student even across days, explicit state/closed constraints, revision and audit history. Windows version 4.3.0.
- Teachers issue from current verified dated lesson and roster, including valid exact relief assignment, with active configured destination, explicit confirmation, server-recorded departure/due time. No attendance marks altered. No movement allowed based on unverified class or identity.
- Staffed destination flow: departure -> arrived -> returning -> returned. Unstaffed flow: departure -> returned. Destination reception granted explicitly by stable numeric destination ID (movement_receive); movement_monitor school-wide read-only, teachers see own issued passes. Admin can record reception and administrative closure with structured reason, not confirmed classroom return. No automatic close at bell or midnight, overdue is due time passed, not a GPS/location claim.
- Board /live/movements/ includes open across days, overdue, date-filtered completed history, scope-preserving student filter and detailed event timeline. New grants don't imply admin/teaching. /manage/movement-destinations/ create/archive; no rename/delete or automatic default grants/destinations. Archived destinations allow existing passes to resolve but block new issue and new reception grants.
- No free-text medical, health, guidance or sensitive personal notes; identity mismatch masks student name and blocks ordinary transitions. Atomic state changes, grant/student locks, CSRF, stale revision and duplicate protection. Source and destination metadata frozen at issue. 
- Code accounts/movement_service.py, accounts/movement_views.py, accounts/test_movements.py, templates/movement_*.html, docs/v4.3-movements.md. Tests cover teacher/destination/monitor scope, direct access, stale revisions, wrong roster/time, duplicate issue, reception flow, unstaffed return, admin closure distinct, archive/revocation, identity change, overdue carryover and CSRF.

### Next actions
1. Verify #320 and latest PR exact-commit CI, and V4.2 Windows artifact. Fix actual failures and update handover. Protected multi-user browser E2E still required; Chrome package check tests fictional website, not protected UI. Validate concurrent issue/transition/revoke, recovery, full school load and performance.
2. Finish movement acceptance: approved destinations/expected times, escalation/notifications, student safety follow-up when original teacher unavailable, explicit supervised handover and correction policies, authorised non-class service visits/early departure/late arrival, data minimisation and approved retention; no inferred location or attendance. Medical/guidance/support casework must be separate with need-to-know controls. 
3. V4.4 Workforce, Relief and Supervision: staff availability/absence and cover, date-specific relief assignment linked to existing ReliefAttendanceAssignment (do not silently reassign existing roll or pass ownership), duty allocation, room changes, calendar exceptions, conflict checks, approvals and auditable notifications; validate school policy and negative access, expiry/cancellation, concurrency. Build on latest cumulative head. Keep central database and fictional mode separation.
4. Prior V4.0–V4.2 acceptance gaps remain: approved SSO/MFA, delegated actions, approved OneSchool transfer, enrolment history and rollback, attendance correction/reconciliation rules, full protected multi-session browser checks, backup and restore drill, ICT/privacy approval. Do not label staging production ready.

## PREVIOUS CHECKPOINT — V4.2 live attendance (27 Nov 2026)

**Latest cumulative branch:** `feature/v4.2-live-attendance`, head `19b992e8656fde195dbaa632e9f82b66dd1c6faf`, draft PR #39 https://github.com/kkieren999/RollFlow/pull/39 (base windows-release, includes previous development phases). Verify current head before edits. This supersedes earlier checkpoints.

### Build status
- V4.0 exact commit 963bf058 run #309 https://github.com/kkieren999/RollFlow/actions/runs/45893460694: all jobs passed; verified artifact 15152018980 https://github.com/kkieren999/RollFlow/actions/runs/45893460694/artifacts/15152018980 (expires 10 Dec 2026 UTC; recheck).
- V4.1 exact commit a664b900 run #314 https://github.com/kkieren999/RollFlow/actions/runs/45893959902: standard and PostgreSQL/native jobs passed; Windows browser step running at inspection.
- V4.2 initial commit bb838e84 run #316 https://github.com/kkieren999/RollFlow/actions/runs/45894265365: standard and PostgreSQL/native passed; Windows queued.
- Latest V4.2 exact commit 19b992e8 push #317 https://github.com/kkieren999/RollFlow/actions/runs/45894329046 and PR #318 https://github.com/kkieren999/RollFlow/actions/runs/45894345367: standard and PostgreSQL/native tests running at last check. Windows artifact name RollFlow-V4.2.0-Live-Attendance-Windows-x64-STAGING; no verified V4.2 artifact yet.
- No merge, deployment, production use, or real data authorised.

### Implemented
- Migration 0019 adds AttendanceRevision.reason and ReliefAttendanceAssignment. Existing rolls/revisions retained. Version 4.2.0 Windows staging.
- Daily attendance summary date selector, unique scheduled valid lesson keys, pending/draft/submitted, overdue after period end, exceptions (ambiguous, unverified, stale publication/roster), latest revision manual reconciliation, non-instructional and malformed allocation counts. Historical view uses active publication only and flags unmatched archived rolls; not an official daily attendance percentage. Future submission before lesson start rejected. Known lunch/recess/break/interval/playground duty/supervision labels excluded, school must validate all instructional categories.
- Administrator-only correction at /manage/attendance/correct/<pk>/ against original frozen roster/identity, requires reason 8–500 chars, exact revision, all valid marks and confirmation; appends new immutable revision and audit, leaves original teacher and submission timestamp, locks old teacher editing. Correction review digest bound to new revision; prior reconciliation stays historical.
- Admin-only exact relief today at /manage/attendance/relief/: reviewed current publication, unambiguous lesson, verified teaching account, no existing roll/overlap, expires end-of-day, regular teacher marking blocked during assignment, no cancellation after roll created; relief actor becomes actual submitting teacher. Existing class metadata grant alone does not allow marking. Restricted to teachers with current verified publication binding; no relief ownership handover or retroactive assignments.
- Admin-only /manage/attendance/student-history/ exact student ID, 31-day date bound, verified submitted lesson marks; missing rolls not inferred as absences; no official daily percentages or exports. Summary viewers get no student names.
- Tests added in accounts/test_live_foundation.py; validate exact latest commit including future marking, completeness, correction preservation/reconciliation, student history and relief scope. docs/v4.2-attendance.md.
 
### First next actions
1. Inspect #317/#318 and #314/#315 and verify artifact presence/expiry. Repair actual failures, update this file. Do not claim completion from pending CI.
2. Finish V4.2 acceptance: exact relief expiry/cancellation/overlap negative tests and two authenticated browser sessions against protected server; concurrency between corrections, publication refresh and roll submissions, performance/load test of full-school dashboard and bounded history. Current browser gate tests fictional website, not protected UI. Verify backup/restore on fictional instance. Audit and refine eligibility/lesson category/grace policy with school; historical missing-roll marking/reconciliation requires approved procedure. No automated overdue notifications or disconnected queue yet.
3. Explicit delegated correction, student-level read/export and reconciliation authority remains admin-only; SSO/MFA and full V4.0/V4.1 acceptance gaps remain (enrolment history/rollback, provider-approved OneSchool transfer, shared network/session policy, data retention). OneSchool review CSV is local only; never claim direct official update.
4. Next major phase V4.3 Student Movements and Services: design server-side movement passes, authorised issuing/arrival/return, current out-of-class list, configurable destinations, outstanding alerts, student movement timelines, school/assigned-class permissions, auditable corrections, no browser-local authoritative records; test negative access and concurrent transitions; no sensitive medical notes in general pass logs. Build from latest cumulative head, preserve prior work and update handover.
5. Prior phases' gates remain outstanding where stated; do not proceed to production until they are reviewed and resolved.

## PREVIOUS CHECKPOINT — V4.1 school data and OneSchool (27 Nov 2026)

**Latest cumulative branch:** `feature/v4.1-school-data-oneschool`, head `a664b900422dbce5683e004a295b0ecb552798d3`, draft PR #38 https://github.com/kkieren999/RollFlow/pull/38 (base windows-release, includes all previous phases). Verify actual head before further edits. This checkpoint supersedes prior phase status below.

### Build state
- V4.0 exact commit 963bf058: #309 https://github.com/kkieren999/RollFlow/actions/runs/45893460694 and #310 both passed standard and PostgreSQL/native checks; #309 Windows browser step still running at inspection.
- V4.1 initial commit b5e5caed: #311 https://github.com/kkieren999/RollFlow/actions/runs/45893836092 passed standard and PostgreSQL/native jobs, Windows in progress. New tests and safety enhancements in 990595b1 and a664b900 remain under validation.
- Latest exact-commit push #314 https://github.com/kkieren999/RollFlow/actions/runs/45893959902 and PR #315 https://github.com/kkieren999/RollFlow/actions/runs/45893967536 started. Verify each job and artifact before claiming success. Artifact name RollFlow-V4.1.0-School-Data-OneSchool-Windows-x64-STAGING.
- No real school data, merge or deployment authorised.

### Implemented
- Admin-only School data centre /manage/school-data/: existing dated CSV, SM110, membership CSV, line alignment, PDF imports and staff identity verification retained; candidate comparison, duplicate/overlap/empty roster diagnostics, applied source freshness and recent import history, publication history.
- Dated snapshot validation version 1. Attendance readiness fails if current applied student/membership batch changes, is missing/purged, or timetable changes; school mode requires actual source provenance. Legacy synthetic fixtures without source refs only accepted outside school mode.
- Identical publish is a no-op; replacing active dated publication with rolls requires explicit acknowledgement. Prior attendance remains attached to original publication. Restore creates a new immutable publication only when exact old digest/sources/snapshot rebuild from current inputs and no affected attendance exists. Full historical import rollback not implemented.
- Migration 0018 AttendanceTransferReview. Admin-only local review CSV for complete submitted revisions, validates frozen roster, original identity, submission history/actor, rejects spreadsheet formulas, stale review digest, invalid identity; audit and one-time operator attestation. No names in CSV; student identifiers restricted to authorised local review. Not OneSchool-approved format, no API/upload or external confirmation.
- Tests appended to accounts/test_dated_school.py and accounts/test_live_foundation.py; verify exact-commit CI. Version bump Windows 4.1.0. Documentation docs/v4.1-school-data.md.

### Next actions
1. Verify #314/#315 and V4.0 Windows #309/#310, investigate actual failures and repair before reporting release. Inspect exact artifact presence/expiry. 
2. Finish V4.1 gaps: full dated student enrolment/withdrawal history and explicit reviewed changes, true import rollback using approved backup/restore procedures, source application locking/concurrency and source freshness regression across all import paths; approved OneSchool transfer format and process from school ICT, not guessed. Test restoration of a real fictional backup.
3. Continue previous V4.0 security gates (temporary relief roster/marking access, delegated action-level permissions, SSO/MFA provider approval, role/session audits, protected browser E2E) and V3.9 protected multi-session workflow; existing Windows Chrome test is fictional training.
4. Next major phase V4.2 Complete Live Attendance: actual all-lesson daily completeness, pending/draft/submitted monitoring, auditable authorised corrections with reason and immutable revisions, exact lesson ownership and relief handling, approved manual reconciliation and re-review after corrections, exception handling and protected multi-session testing. OneSchool remains official; never represent local CSV as approved direct transfer. Distinguish implementation from successful builds and production approval.
5. Keep this file current on development-handover branch. Do not overwrite main or windows-release without review/approval.

## PREVIOUS CHECKPOINT — V4.0 security foundation (27 Nov 2026)

**Latest cumulative development branch:** `feature/v4.0-accounts-roles-security`, head `963bf058d32ff67d8173caf69ce7bd96a5631e51`, draft PR #37 https://github.com/kkieren999/RollFlow/pull/37 (base windows-release; includes prior drafts). Do not restart from main, windows-release or V3.9 for subsequent development. Recheck actual branch head before edits. Sections below retain the earlier roadmap/history; this checkpoint supersedes older statements of current phase.

### Verified build state
- V3.9 repair d3940a8: run #304 https://github.com/kkieren999/RollFlow/actions/runs/45892929577 — tests and PostgreSQL/native succeeded; Windows job now confirmed completed success, including package and browser gate. PR run #305 was still uploading at prior inspection. Verify artifact availability/expiry before reporting download.
- V4.0 first commit 082e5fec: tests failed on unrelated flaky year-scope assertion: the random CSRF token contained substring Y8, not a leaked table cell. Confirmed exact match in log job 140160972140. Repaired in 963bf058 using exact authorised projection and rendered HTML cells, retaining no-private-staff-code assertion.
- V4.0 second commit 6cbbfbad: standard tests job 140161285080 and PostgreSQL/native succeeded in run #307; Windows packaging in progress.
- Latest exact-commit run #309 https://github.com/kkieren999/RollFlow/actions/runs/45893460694 and PR run #310 https://github.com/kkieren999/RollFlow/actions/runs/45893468770 are in progress; #309 standard tests passed, PostgreSQL/native running. Windows package name RollFlow-V4.0.0-Accounts-Roles-Security-Windows-x64-STAGING. No verified V4.0 artifact yet.

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
3. Work from the latest cumulative Windows development branch, presently `feature/v5.0-production-launch-candidate`. For a new phase, create a feature branch from the verified cumulative head. Inspect other overlapping branches before merging. Use an expected-head lease when updating a branch.
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

| Prior cumulative V4.0 development source | `feature/v4.0-accounts-roles-security` — `963bf058d32ff67d8173caf69ce7bd96a5631e51`, draft PR #37 |

| Prior cumulative V4.1 development source | `feature/v4.1-school-data-oneschool` — `a664b900422dbce5683e004a295b0ecb552798d3`, draft PR #38 |

| Prior cumulative V4.2 development source | `feature/v4.2-live-attendance` — `19b992e8656fde195dbaa632e9f82b66dd1c6faf`, draft PR #39 |

| Prior cumulative V4.3 development source | `feature/v4.3-student-movements` — `456a481e0d919711139bb6dde2a918ab281b90d3`, draft PR #40 |

| Prior cumulative V4.4 development source | `feature/v4.4-workforce-relief-supervision` — `9284383eae9ea3b6148174cea509f5c41e1a4e28`, draft PR #41 |

| Prior cumulative V4.5 development source | `feature/v4.5-classroom-student-support` — `4b0348637e54617723ff77f3be965e6340f5bb8e`, draft PR #42 |

| Prior cumulative V4.6 development source | `feature/v4.6-leadership-reporting` — `1926ef6704134ac734408b67b9d3567525f0c197`, draft PR #43 |

| Prior cumulative V4.7 development source | `feature/v4.7-windows-installer` — `a511ec7dea58bdf6108cb62bbc07ae7a433698d4`, draft PR #44 |

| **Current cumulative development source** | `feature/v5.0-production-launch-candidate` — `d8c7811955faa7ddb68217a9441a42e35925c18b`, draft PR #45 |

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
