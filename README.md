# RollFlow V3.8 — School Management System (Windows staging)

See [Windows rebuild and mode boundaries](docs/v3.8-windows-rebuild.md). Start RollFlow.cmd opens the complete offline website; protected database testing has a separate launcher.

# RollFlow V3.6.4 — Real OneSchool export layouts (draft)

This integration branch contains **both** the Windows PostgreSQL password-file
ACL fix from [draft PR #1](https://github.com/kkieren999/RollFlow/pull/1) and
the protected Connected Teacher Portal from
[draft PR #2](https://github.com/kkieren999/RollFlow/pull/2).
Neither PR has been merged and `main` is unchanged. Windows CI builds an
offline `RollFlow-V3.6.1-Windows-x64-STAGING` artifact, checks that
`initdb` can access its private temporary password, migrates the schema,
verifies the authenticated teacher-week route and staff-link column, and
backs up PostgreSQL. Only fictional data are authorised for testing.

**For home testing:** use the independent directory/state instructions in
[deployment/README.md](deployment/README.md) to avoid modifying an existing
working V3.5 installation. Verified OneSchool links and the published timetable
are stored in the school instance database. In live school mode, old links
start unverified; a school administrator must affirm a staff-ID link before
the teacher can see assigned lessons. Actual attendance, data-sharing approval,
release signing, clean-machine upgrade/restore and production readiness are
outside the scope of this staging build.

## V3.5 — Self-contained school architecture foundation

## V3.6.4 — Actual OneSchool export layout support (draft)

The protected Import Centre can now parse a complete **seven-file
TTLineAlignmentExport XLSX** collection and the **TTStaffTimetable PDF**,
both observed from actual OneSchool export structures, without storing
authentic sample data in source control. Original files are archived
encrypted locally, and administrators must review and explicitly approve
their extracted class information.

- TTLine workbooks: day/period Class–Teacher–Room blocks, Year/Line groups,
  missing-staff/room cells, LineNr and TimetableVersionId consistency.
- Staff PDF: per-staff printed codes, class names and class legends,
  timetable version footer; names are **not** copied into evidence tables,
  and no staff code grants a teacher login.
- ExportStudentClass: existing student EQIDs can be matched to class
  codes from the latest approved seven-line snapshot and an approved PDF
  of the matching timetable version. Unknown/inactive IDs remain
  unassigned for review.
- The existing SM110 student directory and date-specific CSV importer remain
  available, and student/class assignments never silently delete existing
  memberships or create unknown teacher profiles.

This is **engineering staging only**. Use generated fictional data for
development and clean-machine Windows tests. Authentic school exports
must remain on an approved restricted host after ICT privacy/security
approval, with archive/key/DB backup and retention processes.

## V3.6.3 — OneSchool ExportStudentClass (CSV, draft)

RollFlow now recognises the exact original OneSchool `ExportStudentClass` CSV:
`EQID,Class_Name`. At **Admin → OneSchool Import Centre → Guided Uploads**
(`/manage/oneschool/documents/`) select **ExportStudentClass** and upload
one UTF-8 CSV. It is encrypted and stored in the same **local-only**
OneSchool archive introduced in V3.6.2; no student records are placed in
GitHub or logs.

**Safe review workflow:** import SM110 students and publish the intended
timetable first. RollFlow matches EQID (including leading zeros) to existing
active student records and Class_Name to class codes in the currently
published timetable or manually created active school classes. The review
screen reports matching pairs, unknown/inactive students and unknown classes.
Only after an explicit administrator confirmation may matched links be
applied; unmatched rows require additional opt-in to skip. A stale preview
is rejected if the matching catalogue has changed.

Approved links live in `OneSchoolClassMembership`, independent of manual
`SchoolClass` teacher allocations and historic `ClassEnrolment` rows.
Admin-only `/manage/oneschool/class-memberships/` allows verification of
class counts and matched students. A later upload is **additive and
idempotent**: it does not remove students missing from the new file, change
attendance, fabricate staff profiles or assign teachers. Reconciliation,
historical start/end dates and teacher-accessible rosters need separate
privacy/education review before school operation.

The V3.6.3 Windows staging package uses its own local state and ports,
rather than overwriting earlier home test installations. It is still an
unsigned engineering build, not approved for identifiable school data.

## V3.6.2 — OneSchool guided import centre (draft)

Administrators can open **Management → OneSchool Import Centre → Guided document uploads**
at \`/manage/oneschool/documents/\`. The page explains what to find in OneSchool,
how to export each source, and exactly what can and cannot be applied.

| Source | Choose in the portal | Current behaviour |
| --- | --- | --- |
| **SM110 Dynamic Student List** | One \`.xlsx\` file with \`Data\` sheet, columns \`Student Name, EQ ID, Roll Class, Year\` on row 5 | Validate and archive, then explicitly approve an ID-matched student directory/home-group upsert |
| **Whole-staff timetable PDF** | One or more PDFs | Validate PDF structure/text layer and securely archive originals; **no automatic teacher/class allocations yet** |
| **TTLineAlignmentExport** | Multiple \`.csv\`, \`.xlsx\`, or \`.pdf\` files in one batch | Validate and keep all parts grouped for review; **no automatic class alignment until the exact schema is verified** |

The **existing OneSchool date-specific Timetable Export CSV importer** is unchanged and remains the supported route for published allocations.

SM110 upserts use exact EQ IDs and are all-or-nothing in a database transaction. The import never deactivates absent students, resets status, changes dates or portraits, removes attendance, or assigns subject-class enrolments. Existing staff-ID verification remains required for live teacher views.

### Protected offline archive and recovery

Originals are encrypted with Fernet using a **per-instance key stored separately from encrypted source blobs**, under \`ROLLFLOW_DATA_DIR\`:

- \`oneschool-imports/<random-token>.rfenc\`: private encrypted source files.
- \`oneschool-import.key\`: local encryption key; **store in protected offline backups separate from the PostgreSQL dump**.
- \`uploads/\`: temporary upload area; never served publicly or placed in static files.

Instance NTFS/Unix permissions are restricted and a user-specific ACL is applied to the archive directory and key on Windows. Uploads and original downloads require authenticated active administrators, and downloads are hash-verified and \`no-store\`. The database stores source metadata/hashes and review summaries, **not raw exports**. Every upload, apply, retrieval and purge is included in existing SecurityEvents. The admin can retrieve an original later or explicitly purge its encrypted copy while retaining audit metadata. A database backup alone does **not** restore archived originals or their key. Establish a local retention schedule and test recovery procedures before school deployment.

Only fictional/synthetic development files and approved de-identified examples belong in personal development installations. Actual school files require school ICT approval, an authorised protected host, and a privacy/security review. Do **not** commit user uploads to GitHub, post them to a ticket, sync the archive to consumer cloud drives or expose local application/database ports.

Development: install \`requirements.txt\`, run \`python manage.py migrate\`, and \`python manage.py test accounts\`. This work targets the separate V3.6.1 integration branch in a **draft PR**; do not merge it into \`main\`. Teacher/class PDF extraction and subject-enrolment allocation are intentionally not enabled until authentic formats can be reviewed safely with fictional equivalents.

## V3.6 — Connected Teacher Portal (draft)

The protected Django Teacher Portal now offers a **My week** view at `/teacher/week/` alongside the existing day-by-day timetable. Both are read-only and display only allocations from the currently *published* OneSchool timetable whose exact `Staff_Id` matches the signed-in teacher's administrator-maintained Staff Profile. Staff codes, query parameters, class codes and browser storage never authorise a teacher's timetable. Personal week data is projected to class, subject, period, time, year and room only; no other staff IDs or raw imported records are sent to the view.

**Administrator verification is mandatory in live timetable mode.** Existing OneSchool staff links are intentionally unverified after migration `0007_verified_timetable_link`. Under Staff Management, edit the staff member, check the OneSchool staff ID against the authoritative staff record, then tick **I verified this OneSchool staff ID against the authorised staff record** and save. Changing an ID without another explicit confirmation automatically revokes verification. Imported or newly created accounts do not receive verification by default. Only authorised administrators can modify this mapping; the operation is logged as a staff-link verification/revocation event. Ambiguous case-insensitive mappings fail closed. The public static demo and non-live development timetable are unchanged.

In live mode teachers cannot open the school-wide Master Timetable route; it redirects to their scoped timetable instead. Administrators retain the full master timetable for publication review. The two views never allow teachers to select another staff ID, user or archived snapshot, and they show clear missing/unverified mapping, no-publication, absent date and expired coverage states. The original fictional attendance interface is still disabled in school mode; **real attendance, student rosters and OneSchool write-back are not implemented**. Do not use live student or staff exports without departmental approval and security review.

Run `python manage.py migrate`, `python manage.py check`, `python manage.py makemigrations --check --dry-run` and `python manage.py test accounts` on this branch. The new teacher security tests cover access rules, missing or unverified links, URL spoofing, exact-ID isolation despite shared staff-code aliases, timetable replacement and administrator verification. Keep this PR in draft pending review and clean Windows installation testing. This branch is based on `v3.0-foundation` and does not include the independent V3.5.1 draft PR unless that work is later integrated.

## V3.5 — Portable school installation foundation

The [deployment guide](deployment/README.md) documents the new offline Windows distribution builder, local PostgreSQL instance runner, separate private instance state, native administrator creation, local static serving, loopback WSGI service, database backup and stricter school configuration. The runtime builder requires verified Windows binaries on a build machine; the finished distribution is intended to require no separate Python or PostgreSQL installation on compatible targets. No signed USB installer or approved production deployment exists yet. Use fictional data only. GitHub Actions adds PostgreSQL and offline dependency checks; consult the actual run results.

## V3.4.4 — Import reliability and timetable bug fixes

The protected importer validates CSV quote placement before parsing and uses a SHA-256 fingerprint of the source bytes with a V3.4.4 prefix. Exact repeated files reuse their new-format version, changed source files create new versions; existing snapshots are retained. Staff IDs/codes are normalized and exact staff-ID lookup is preferred when available. Navigation bounds dates to 1900–2099, warns when the published coverage is expired or not yet started, and counts visible allocations after the break filter. The protected server retains archived versions and does not expose deletion. The browser edition requires publishing a replacement before removal and synchronizes committed versions across tabs on the same origin.

Regression tests have been added for source-level identity, malformed quotes, duplicate counts, date bounds, coverage warnings and staff lookup. The GitHub Actions V3 foundation workflow supports manual dispatch. Run `python manage.py check`, `python manage.py makemigrations --check --dry-run`, and `python manage.py test accounts` with dependencies installed. Although Django could not be installed in the original editing environment, [GitHub Actions run 44614590326](https://github.com/kkieren999/RollFlow/actions/runs/44614590326) verified commit `9cdea39fa54936752299bbafc94d94b91fa6d32f` on 20 November 2026 (Brisbane time): Python 3.12 dependencies installed, Django 5.2.19 loaded, system checks reported zero issues, no migrations were missing and all 42 `accounts` tests passed. This run used the development SQLite configuration; PostgreSQL, a private HTTPS deployment and production readiness remain unverified.

## V3.4.3 — Usability and stability

Published import statistics are shown separately from manual directory records. The dated Master Timetable has week navigation, Today, first imported day, staff/room lookup, filtering/highlighting, compact/expanded layout, and current-period indicators. The teacher timetable remains restricted to the linked staff ID. Staff, student and class directories support server-side sorting over the full matched queryset and retain filters across pagination. Other admin tables support client-side sorting and pagination over their loaded records. The timetable management tab is remembered in the session.

Frontend syntax and focused synthetic rendering checks passed. Additional Django regression tests cover dashboard statistics, staff/room filtering, personal timetable scope, tab persistence and sorting. The full Django suite still needs to be run in the server or CI environment; this is not a verified production deployment.

## V3.4.2 — Operational timetable publication

For operational school use, school ICT must provision a private HTTPS application host and PostgreSQL database, approve access, confidentiality and retention controls, run migrations and the complete regression suite, and provision individual accounts. Configure the non-debug environment variables below, a random secret of at least 50 characters and `ROLLFLOW_LIVE_TIMETABLE=1`. This flag does not itself establish approval or production readiness. Do not place school exports in GitHub.

The operational OneSchool Import Centre has one primary action: **Import & publish timetable**. Administrators enter a version name, choose the original full-size CSV and confirm authorisation and full-snapshot replacement. CSV schema validation and atomic publication are retained; earlier versions can be reviewed and republished. No draft requirement, sample-download control or temporary testing screen is exposed in operational mode. The teacher landing and master timetable display the published snapshot or a clear unpublished empty state, and unfinished administrative modules are hidden. Individual teaching schedules require a verified OneSchool Staff_Id link. Live class membership/attendance, automatic reconciliation into the manual directories and OneSchool write-back are not enabled.

The static browser demo is distinct: it publishes a persistent masked timetable to local IndexedDB only. The development server keeps non-operational regression fixtures and test controls for engineering verification; they must not be used as school records.

## V3.4 — OneSchool integration and advanced timetable management

Install requirements and run `python manage.py migrate` and `python manage.py test accounts`. Sign in as an administrator and open OneSchool Import Centre. Download the synthetic sample or use an approved de-identified CSV. The importer supports the 15-column OneSchool Timetable Export (UTF-8 CSV, DD/MM/YYYY, Mon–Fri, 24-hour HH:MM; 20 MB/150,000 rows maximum). No original export, MISID or staff names are retained; class/subject/year, date, period/times, staff ID/code and room code/name are stored in a protected date-indexed snapshot. Overlapping allocations and missing resources are warned about, not automatically rejected. Exact normalized duplicates are dropped; repeat identical snapshots reuse the existing version.

Review counts, date range, warnings and sample rows before publishing. A publication replaces the entire previously published imported snapshot. Prior versions are retained and can be republished after review. Missing dates show no imported lessons; there is no implicit recurrence or merge. Imported snapshots do not overwrite existing manual staff/class/room/period records or create accounts. Link an authorised teacher account using the approved OneSchool Staff_Id in Staff Management (case-insensitive exact match; verify the identity before linking). Master Timetable and School timetable display the published dated data, and personal schedules are filtered by the linked staff ID. The recurring planning view is used only before a first publication.

Timetable Management has Overview, Lesson allocations, School periods, Rooms, Versions and Import sections. School periods in the manual timetable are not automatically edited by imported bell times. Date-specific period windows are preserved in the imported timetable. Shared staff/room assignments do not establish availability or authorised relief. Full imported class membership, student/staff directory reconciliation, relief, attendance submission, effective-dated publication automation, resource availability and school approval remain pending. Use fictional or approved de-identified data in development; no real school exports in GitHub. Backend integration tests are committed but require execution in a Django environment.

## V3.3.1 — Master Timetable

The database-backed whole-school timetable is available from /manage/master/ for administrators and /teacher/master/ for authenticated teachers. It displays active recurring slots, periods ordered by start time, weekday tabs, year-level groups, class/teacher/room search, hide/show breaks (recognised by the period label or code), slot details, staff and room clash counts, and available-resource counts. Administrators can navigate to class and slot editing; teacher access is read-only and does not expose student rosters. Removed periods and inactive allocations are excluded. Resource counts use active teaching accounts and rooms for the full selected day, not filtered search results.

The master timetable is recurring weekly planning rather than an effective-dated, published timetable version. Date-specific changes, shared-resource exceptions, authorised relief and timetable publication/version management remain planned. Backend regression tests are included; run migrations and the Django test suite before deployment. The separate public demo uses fictional browser-local planning only.

## V3.3 — Class & Timetable Management

Apply migrations with `python manage.py migrate`. Administrator-only Class Management and Timetable Management create relational school classes, primary teacher allocations, dated student class enrolments (end instead of delete), rooms, school periods and recurring weekly lesson slots. Six example periods are seeded, using the previous fictional RollFlow teaching day. Staff and student records must be created before class allocations. Primary teacher changes do not silently reassign existing timetable slots. Class codes stay stable. Draft codes on staff profiles remain legacy planning notes, not permissions.

Add a room, create a class, enrol students, and create or import lesson slots. The CSV template uses `class_code,teacher_username,room_code,weekday,period_code`; 1–5 are weekdays, all references must exist and be active where applicable. Maximum 500 rows/250 KB. Transactions reject invalid imports, and database constraints prevent active teacher/class/room double-booking within a period. Period time overlaps are validated in the form. Student timetable clashes, term calendars, date-specific exceptions, period-edit concurrency controls, full timetable history and relief allocations remain planned.

A signed-in teacher can open School timetable from the Teacher Portal, a protected read-only weekly view based on assigned active database slots. Teachers cannot modify the planning records or see other teachers' slots through this endpoint. Central student rosters and attendance saving are not connected to the existing fictional roll workflow yet. New development databases begin without staff/student/class/room records other than seeded periods and the initial role group. The public Pages demo continues to use fictional browser-local planning and attendance data.

Backend regression tests are committed for class editing, enrolment history, conflicts, transactional import, access control and teacher timetable filtering; run the Django checks and tests before deployment. Do not use actual school data.

## V3.2 — Student Management

Install updated requirements and apply migrations with `python manage.py migrate`. The server's administrator-only Student Management module includes a central database model and directory, student profile editing, year/home group/status filtering, enrolment and leaving dates, photo upload/removal and a transactional CSV import. New server databases start with no student records; import fictional samples using the supplied CSV template. The public demonstration has 240 fictional fixture students.

Photos accept JPEG or PNG up to 5 MB and 16 megapixels, are resized to fit 480 × 640 and re-encoded as JPEG without preserving original metadata. The image is stored in the school-hosted development database, not GitHub, and delivered through an administrator-authorised no-store endpoint. Neither the public demo nor the server development installation is approved for real student records. Teachers cannot query this central directory yet.

CSV header: `student_id,first_name,last_name,preferred_name,year_level,home_group,status,enrolled_on,left_on`. Year levels 7–12; status active, inactive or left; dates YYYY-MM-DD. Duplicate or invalid rows reject the entire import (500 rows/250 KB maximum). Student identifiers are immutable in the form. Status and enrolment dates can be changed without deleting the student. Staff/student events appear in management activity history; this is not a complete enrolment-history or tamper-resistant attendance audit.

Teaching-class enrolments and historical transfers, teacher access rules, central timetable integration and attendance records remain planned. The V3.2 code adds student administration tests and migration files; run the Django checks and test suite before further deployment.

## V3.1 — Staff management

After running `python manage.py migrate`, sign in through Admin login. The authenticated administrator is directed to `/manage/`, the RollFlow-branded staff portal. The existing Django administration site remains at `/admin/` for advanced administrative tasks. The new portal includes dashboard account counts, searchable/paginated staff directory, account creation and editing, Teacher/Administrator role changes, password reset, activation/deactivation, staff profile information, draft class allocations, CSV import and recent account activity.

Staff imports accept only the UTF-8 header `staff_id,username,first_name,last_name,faculty,campus`, up to 200 rows and 200 KB. Import is transactional and duplicate IDs/usernames are rejected. Every imported account is inactive with an unusable password; administrators must reset passwords before activation. Draft class codes do not grant class access; actual class/timetable relationships are planned for V3.3. No real staff information should be imported. The two roles are intentionally broad for testing, and administrator accounts are full Django superusers. Least-privilege roles, SSO/MFA, secure audit retention and production controls need later development. The staff API checks administrator access and uses CSRF-protected mutations; deactivation, role changes and password resets revoke affected database sessions. Staff account events are logged without passwords.

The public Pages demonstration remains on main; its staff changes are browser-local and do not create server accounts. Student management, classes, timetables, relief, attendance monitoring, movements, reports and school settings are navigation placeholders pending later stages. The backend test suite includes authentication and staff-management tests; run it with the instructions below.

**Development branch: v3.0-foundation.** This is an application foundation for fictional testing, not a production release or authorised school attendance system.

The existing public GitHub Pages site on the main branch continues to use the fixed public demo credentials (teacher / teacher and admin / admin). The Django server does not accept those credentials unless an administrator deliberately creates such an account; do not do that. Real school credentials, photographs and records must not be used here.

## Run the development server

Prerequisites: Python 3.12, Git and access to install the dependencies. Run on your own computer, bound to loopback only.

```sh
git clone --branch v3.0-foundation https://github.com/kkieren999/RollFlow.git
cd RollFlow
python -m venv .venv
# macOS/Linux:
source .venv/bin/activate
# Windows PowerShell instead:
# .venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

macOS/Linux: `export ROLLFLOW_DEBUG=1`

Windows PowerShell: `$env:ROLLFLOW_DEBUG="1"`

```sh
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver 127.0.0.1:8000
```

Choose a unique administrator username and strong password at the prompts. Open http://127.0.0.1:8000/ and select the Admin login cog. The administrator overview is RollFlow's database-backed management interface. Select Staff Management → Add staff, enter fictional staff information and a strong password, select Teacher and activate the account. Staff ID, faculty and campus can be managed on this page. Sign out, then sign in through the teacher login. Account names are assigned by the administrator, not editable in the teacher workspace. Disable accounts instead of deleting them.

## What is implemented

- Django database-backed user accounts, Teacher group and administrator authentication.
- Separate login routes, Cog link, server-side role checks, POST-only CSRF-protected logout, database sessions, Argon2 password hashing and database-backed login throttling.
- Login/logout events and Django's administration change log; these logs are not a complete or tamper-resistant attendance audit.
- Admin management of users, account activation, passwords, groups and optional staff profiles.
- The existing teacher UI receives its authenticated identity from the server. The public demo mode is retained when opening the static file alone.
- The teacher workspace is explicitly a fictional browser sandbox, with distinct localStorage keys per server account. Local browser keys are **not a security boundary**. Student/class data is still synthetic and hardcoded, and live roll submission, student access permissions, supervision authorisation, profile/preferences synchronisation and attendance data APIs are not implemented. The teacher page is server-authenticated but records are not centrally persisted.
- An initial schema/migrations for accounts and security events, with PostgreSQL configuration for later multi-user work.
- An automated test suite and a GitHub Actions workflow.

## Test

With the same development environment configured:

```sh
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test accounts
```

The checks cover login, role restrictions, account deactivation, logout, CSRF and rate limiting. Run browser tests on laptops and iPad Safari separately.

## School ICT configuration — not a release procedure

For non-development configuration, leave ROLLFLOW_DEBUG unset and supply the following variables through an approved secret/configuration manager:

- ROLLFLOW_SECRET_KEY (unique secret with sufficient entropy)
- ROLLFLOW_ALLOWED_HOSTS (specific internal hostnames; no wildcard)
- ROLLFLOW_DB_NAME, ROLLFLOW_DB_USER, ROLLFLOW_DB_PASSWORD, ROLLFLOW_DB_HOST, ROLLFLOW_DB_PORT

Use an approved PostgreSQL server, a restricted OS service account, TLS, an approved WSGI server/reverse proxy, private network access, secure static-file serving after `python manage.py collectstatic`, and encrypted backups. Only enable ROLLFLOW_TRUST_HTTPS_PROXY=1 behind a proxy that strips untrusted forwarding headers. Review rate limiting for shared school IPs and expire old LoginWindow rows under an approved retention policy. Run `python manage.py check --deploy` and remediate findings. Do not expose Django's development server to a school network.

Before production: integrate school-approved SSO/MFA, separate administrative permissions, secure student/class/session data models, central attendance transactions and corrections, server-enforced teacher and supervision permissions, tamper-resistant audit, authorised imports, cross-device synchronisation, security/accessibility testing, records retention and backup restore testing. Confirm with departmental ICT whether and how RollFlow may operate alongside OneSchool.

GitHub stores application code and fictional test fixtures only. Databases, secrets, backups and real school information never belong in the repository. .gitignore is a safeguard, not a data protection boundary.

## Previous teacher demo

The original minimal portrait grid, photo-tap marking, single Save button, date-aware timetable, Class Finder supervision pins, Student Movements, accessible preferences, permanent navigation and teacher profile are retained. Static demo behaviour on GitHub Pages remains on main.
