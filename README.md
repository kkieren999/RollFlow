# RollFlow V3.0 — School application foundation

## V3.4.1 — Direct timetable publishing

The GitHub Pages site remains fictional. Its temporary Test Import accepts the original CSV structure up to 20 MB/150,000 rows, displays masked identifiers and does not publish or retain test results. Use school-approved data only.

For actual school timetable publishing, school ICT must provision a private HTTPS application host and PostgreSQL database, approve access, confidentiality and retention controls, run the migrations and entire test suite, and provision individual staff accounts. Set the non-debug configuration variables documented below, a randomly generated secret of at least 50 characters, and `ROLLFLOW_LIVE_TIMETABLE=1` only on that approved installation. Never use the demo credentials or commit real exports. The new flag rejects debug/SQLite configurations. It does not itself establish approval, secure hosting or production readiness.

Administrators can then select OneSchool Import Centre, enter a version name, choose the original full-size CSV, confirm authorisation and acknowledge full-snapshot replacement, and select Import & publish timetable. The original rows are validated before any publication; earlier published snapshots are retained. Review mode remains available. Teachers see the published timetable rather than fictional attendance when live mode is enabled. Class memberships, live roll marking and OneSchool write-back are not implemented. This release is a timetable-only pilot candidate, not a certified attendance system.

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
