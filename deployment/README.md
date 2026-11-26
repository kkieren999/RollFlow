# V3.8 Windows package — start here

**Start RollFlow.cmd** opens the complete bundled website offline using fictional data. **Protected Workspace.cmd** opens a menu for fresh database-backed staging or backup-first upgrade of the existing database. See [V3.8 rebuild notes](../docs/v3.8-windows-rebuild.md). Old instructions below refer to earlier packages and their original shortcuts. Never use real records in staging.

## Authoritative school data (V3.7.0 staging)

1. In the private server, use the OneSchool timetable CSV import and publish the complete dated export.
2. Review and apply the authorised SM110 student directory and ExportStudentClass membership report separately. A timetable contains allocations, not student enrolments. These reports may be added later: timetable-only publication creates no invented student rosters.
3. Open **Dated OneSchool publication**. Missing staff IDs can be prepared as inactive accounts with unusable passwords. Verify each exact official staff ID, set password, grant teaching access independently of the role, then activate. No identity is inferred from names or staff codes.
4. Review the counts, skipped memberships, unmapped staff and exact date coverage. Confirm the connected publication. It becomes the source for the master timetable, class directory, daily/weekly schedules and scoped rosters. No weekly repetition fills absent dates. A new export does not alter the reviewed connected snapshot until republished.
5. The protected server remains read-only for actual attendance, movement and relief changes. These must be implemented and tested against the private data model before deployment.

# V3.7.0 staging — website parity

The Windows release branch packages the exact public Pages snapshot in `app/training` alongside the protected Django/PostgreSQL application. Use **Open Training Demo.cmd** to launch the fictional training workspace on a separate loopback port (18086). Do not use the training workspace for real data. It does not share browser storage with the protected application. The protected application continues to use **Start RollFlow.cmd**.

`BUILD-INFO.json` records both Windows source and website commit hashes; `SHA256SUMS.txt` records bundle file digests. Retain existing private state and extract a new bundle separately before running **Upgrade Existing.cmd**. Do not run First Setup over existing state. Staging is not a signed or school-approved production release.

For later website releases, fetch the public main branch and run `python deployment/sync_training.py --ref origin/main` in the Windows source checkout. Review and commit the tracked training directory. CI verifies the exact pinned website bytes before publishing a staging build.

# Recording services in the student day template (offline demo)

The V3.6.7 Windows staging **fictional browser fallback** now uses the same
movement log as its searchable student day template. When an example student
uses a service, the template displays the destination, departure/return
status and duration under Care class or the correct Period 1–4 based on
the recorded Brisbane time. New passes also store a session identifier for
consistent grouping. The Movement log provides a **View in template** control
that opens the matching student and date; names of students with recorded
visits on that date are also offered as shortcuts. No-visit period cells
remain blank, and records outside the five periods remain visible.

The feature changes only offline demo UI and browser-local fictional passes.
The authenticated Django/Windows connected-school system does not share this
data or receive this new template automatically. Installing an approved
Windows staging build requires backup-first manual upgrade instructions below.

# Student movements by period — Windows offline demo

The fictional browser-based fallback teacher UI packaged in the Windows
V3.6.7 staging bundle has a student lookup **below Movement log**, with a
read-only five-row **Care class through Period 4** template. Existing sample
and browser-issued passes are grouped by departure time on the selected date,
with empty period cells where no movement was recorded. Multiple passes per
period remain visible and out-of-period visits are listed separately.

This is matching demo source, **not** a new connected-school Django route,
not a PostgreSQL movement register, and not an automatic Windows update.
An approved Windows bundle must pass staging tests and be installed through
the backup-first manual upgrade process below; real school records must never
be entered into the public fictional demo.

# Administrator-managed movement destinations — V3.6.7 offline demo

The offline fictional browser UI shipped as `index.html` now provides
**Student Movements → Manage movement destinations** in its demonstration
administrator interface. Destinations may be added or removed (with
validation, duplicate prevention, and at least one required option);
the teacher demo uses the resulting list for new passes. Removing a
destination preserves past movement logs and historical student filters.

This is a browser-local demonstration feature, **not** a centrally
managed Windows/Django school setting. It does not grant management
permissions in the authenticated connected-school Django portal,
which does not currently implement production student movement passes.
The public demo's `admin / admin` is not secure authentication, and
changes made on GitHub Pages do not travel automatically to a Windows
installation. The updated offline demo must be bundled in a new,
successfully tested Windows staging build and applied by an approved,
backup-first manual upgrade; do not run First Setup on existing data.

# Student Movements Example 1 — Windows bundle and GitHub Pages parity

The **fictional browser-local Student Movements demo** in this branch's `index.html`
now has the same Example 1 compact dashboard as GitHub Pages, including the
three movement counters, student search, destinations, Issue pass, duration,
Returned actions and the All / Currently out / Returned filter. Source parity
does **not** imply installed-app parity or shared data.

**What Windows actually runs:** `deployment/build_windows.py` includes
`index.html` in the offline bundle. The protected Django `/teacher/` route
renders that demo only for eligible teachers with **no connected publication**.
When a connected timetable is active, teachers are redirected to the
independent Django timetable and roster views; those do not yet have a
production student-movements backend or this demo page. Do not use a browser
demo to record real student movements.

**A GitHub push does not update a user's existing Windows installation.**
To apply this source change to the offline staging bundle, obtain a **new
tested V3.6.7 Windows-x64 STAGING artifact** built from the updated
`feature/v3.6.7-unified-ui` branch. Confirm the artifact's workflow completed
successfully. On the machine, with appropriate IT authorisation:

1. Stop RollFlow first; back up the local staging instance and any data.
2. Extract the *new* bundle to a **separate directory**, keeping the previous
   directory because the PostgreSQL configuration may refer to its runtime.
3. Run `Upgrade Existing.cmd` from the new bundle. It creates a private
   backup and checks migrations. **Never use First Setup.cmd on an existing
   instance.**
4. Start with `Start RollFlow.cmd`; test the protected login and existing
   timetable in the new bundle on the isolated staging port `18085`.
5. If needed, roll back only according to your authorised restore procedure;
   do not overwrite or delete the prior PostgreSQL runtime directory.

The staging database under
`%LOCALAPPDATA%\\RollFlow-V3641-Staging` is **not** the website's localStorage.
No school records, credentials, timetable allocations or data synchronisation
are transferred by this visual update. A secure shared backend, authenticated
movements feature and a separately approved Windows update mechanism would be
required for automatic multi-device parity. Never commit school data or private
archives to the public GitHub repository.

**Student Movements cleanup (fictional demo):** The V3.6.7 offline fallback demo now matches GitHub Pages: it no longer inserts **Daily Service Usage**, **Students Using Each Service**, or **Visits to Each Service** above the dashboard. The earlier 6–10 visits-for-every-student generated history is replaced by a smaller set of 18 selected fictional students with varying levels of completed visits, including frequent users (10–15), occasional users (3–6) and infrequent users (1–2). These show as clearly labeled **Fictional sample** in the dashboard log and in student histories. Existing browser-issued passes and unrecognised user-modified history are not overwritten. The connected-school Django installation remains separate, and updating source does **not** update an installed Windows instance automatically.

# V3.6.7 — Unified Teacher & Administration Interface (draft staging)

This is a UI-only update on top of V3.6.6: shared offline design tokens,
administrator and teacher navigation, page layouts, tables, forms, focus
styles, responsive handling and version labels. No school records, account
roles, imported files, published timetable allocations, or database schema
are modified by these UI changes.

For an existing instance: stop RollFlow, extract the new Windows bundle into
a NEW directory, retain the previous extracted directory because instance.json
holds the PostgreSQL runtime path, run Upgrade Existing.cmd for a new private
backup and migration checks, then start with Start RollFlow.cmd. Never run
First Setup on an existing installation. The native staging state and port
remain %LOCALAPPDATA%\RollFlow-V3641-Staging and 18085.

See deployment/UI_AUDIT_V367.md for route-by-route functional and responsive
review. Existing OneSchool archive and current teacher timetable are preserved.

# V3.6.6 — Automated School Setup (draft staging)

Stop the existing instance, extract the new package separately, keep the
previous PostgreSQL runtime folder, run Upgrade Existing.cmd, then Start
RollFlow.cmd only after successful upgrade. This reuses V3641 staging state,
port 18085 and the protected archive. The backup-first upgrade applies
migration 0012. Do not run First Setup on existing data.

Open /manage/connected/setup/ as an administrator. Verify PDF period
suggestions, missing/conflicting grids and staff candidates. Select eligible
staff to create inactive users with unusable passwords. Set each individual's
password using the existing reset screen. Then explicitly supply each
authorised OneSchool Staff ID and confirm identity and teacher eligibility
before bulk activation. No inferred ID, shared password, automatic activation
or automatic overwrite. Existing accounts require manual review and mapping.
Review and republish connected school data to activate new mappings.

Lesson times are editable; term and closure dates remain administrator-entered.
Other period types remain evidence only. Use fictional records for home tests.
School data requires authorised ICT/privacy/security review.

# V3.6.5 — Connected School Data (staging)

## Upgrade your existing V3.6.4.1 / .2 / .3 test instance

1. Stop RollFlow using Ctrl+C and wait for the database to stop.
2. Extract V3.6.5 into a **new application folder**. Keep the old extracted
   folder because instance.json points to its PostgreSQL runtime.
3. Run **Upgrade Existing.cmd**. It refuses to proceed while PostgreSQL is
   running, uses the existing %LOCALAPPDATA%\RollFlow-V3641-Staging state,
   copies the encrypted originals and key into a new private
   upgrade-backups directory, creates and checks a PostgreSQL dump, then
   applies additive migration 0011 and runs Django checks.
4. Only after successful upgrade, run **Start RollFlow.cmd** and visit
   http://localhost:18085/manage/connected/. Do not click First Setup.
   Do not delete original state or the old code. For custom state paths
   use the explicit command below.

```powershell
.\python\python.exe -m deployment.native --state "$env:LOCALAPPDATA\RollFlow-V3641-Staging" upgrade
```

The backup is local and permission-restricted, not automatically encrypted
as a whole. Keep a separate approved encrypted offline copy and rehearse
restore; the dump check only validates its table of contents, not a full restore.
Do not expose or sync backups. If upgrade fails, stop and retain the backup.
An actual restore/rollback must be performed by a qualified administrator.

## Publish connected data

In OneSchool Import Centre select **Review and publish school data**.
All four source types must be approved; latest line and staff PDF versions
must match. Confirm the selected batch references. Verify teacher Staff IDs
in Staff Management, then explicitly map printed staff codes to verified
teacher accounts. Enter term start/end, all 20 weekday period times
(Day,Period,HH:MM,HH:MM, no header) and closure dates. Review, then publish.
The existing Classes and Master Timetable links now show the publication.
Teacher login, My day and My week use only verified, published allocations.
Class rosters are read-only and limited to the teacher's verified weekly
slots within the current term; PDF-only classes are administrator-only.
New import changes require a new review/publication. Earlier snapshots,
manual records and original archive files are preserved. Latest original
SM110 and student-class CSV must remain available for reconciliation.

The weekly line exports omit relief, assemblies and non-line periods; this
is a term planning timetable, not an authoritative live daily attendance
feed. No attendance writes. School data requires an authorised host and
ICT/security/privacy review. Use fictional records on home staging.

---

# V3.6.4.2 — Staff PDF empty-legend fix

This is a code-only bugfix for V3.6.4.1. A staff page with no classes can
contain only Class Code and Class Name headings followed by a report footer;
the parser now counts this as empty instead of failing. Nonempty malformed
tables still fail validation. Missing/empty legends require administrator
acknowledgement before approval.

The schema and V3.6.4.1 state path/ports are unchanged deliberately. Do not
run First Setup again on an existing instance. Stop the old instance,
back up its database, archive and key, and start the corrected code from
a separately extracted folder with Start RollFlow.cmd. Do not start both
copies concurrently. A previously staged PDF can be reviewed again directly.

---

# V3.6.4.1 — Fix for OneSchool Excel worksheets without dimension metadata

Some genuine OneSchool TTLineAlignmentExport XLSX files omit the optional
worksheet dimension reference. Older V3.6.4 builds raised a TypeError on
upload when the streaming Excel reader returned a missing row count. V3.6.4.1
accepts that format, checks rows with explicit bounded iteration, and applies
the same fix to SM110 student-list Excel files. Original imports still need
administrator review before records are applied.

For an isolated clean test, extract the V3.6.4.1 staging ZIP to a new
folder. Run **First Setup.cmd** once and then **Start RollFlow.cmd**.
New staging state: `%LOCALAPPDATA%\RollFlow-V3641-Staging`.
Local URL: **http://localhost:18085/**. PostgreSQL: **55437**.
Do not delete or overwrite your V3.6.4 database or archives.
Use only fictional files in a home test. Live OneSchool records require an
approved private school host and a privacy/security assessment.

---

# V3.6.4 — Verified OneSchool source layouts (draft)

Use the new independent Windows staging folder, not any prior RollFlow
installation. Launchers use `%LOCALAPPDATA%\RollFlow-V364-Staging`,
PostgreSQL port **55436** and local web port **18084**. Run `First Setup.cmd`
only once, then `Start RollFlow.cmd` and browse http://localhost:18084/.

### Actual OneSchool file import order

1. **SM110 Dynamic Student List**: upload the original active-student
   XLSX with Data worksheet columns Student Name / EQ ID / Roll Class / Year.
   Review and approve student directory changes.
2. **TTLineAlignmentExport**: select all **seven** XLSX files at once using
   Ctrl/Shift. These contain different line numbers 1–7 from the same
   TimetableVersionId; review the parsed day/period slots, blank staff and
   room cells, then approve the class-timetable evidence.
3. **TTStaffTimetable**: upload the full staff-timetable PDF as **one file**.
   Review the extracted staff/class legend evidence and pages without a
   class legend, then approve. This does **not** link staff to logins.
4. **ExportStudentClass**: upload the two-column `EQID,Class_Name` CSV.
   RollFlow compares identifiers against the **active SM110 directory**
   and classes against the reviewed line and PDF catalogues. Explicitly
   review unmatched/inactive EQIDs and unrecognised class codes before
   approving additions.
5. Optionally use the existing **date-specific OneSchool Timetable Export CSV**
   to publish the dated teacher schedule. TTLine weekly slots are not a
   substitute for date-specific published lessons.

Approved line slots and PDF class evidence are stored in PostgreSQL, original
files are encrypted locally under `oneschool-imports/` with a separate key,
and every approval is audited. Unmatched student IDs are never fabricated.
No teacher account is verified or granted student information access based
on raw PDF or line staff codes. Later imports do not silently delete existing
class memberships.

**Use fictional exports in home testing.** Real OneSchool data requires
the approved school host, ICT review and authorised retention/backup controls.
Keep the encrypted archive AND its key alongside database backups. Never
commit the actual school exports to GitHub.

---

# V3.6.3 — Student-to-class enrolment CSV import (draft staging)

The guided Admin Import Centre now accepts the official OneSchool
`ExportStudentClass*.csv` format with two columns: `EQID,Class_Name`.
Import the fictional SM110 student list first and publish the corresponding
fictional timetable CSV (or create authorised school classes). Then
**OneSchool Import Centre → ExportStudentClass** uploads the original CSV
into the locally encrypted offline archive. Review matched, missing and
inactive EQIDs and unmatched class codes before applying. If unmatched rows
exist, they are skipped **only** with an explicit administrator acknowledgement.
The importer adds idempotent membership records without deleting existing
links or inventing students, classes or teacher account assignments.
This is not a live attendance-writing system.

V3.6.3 Windows staging shortcuts use separate state
`%LOCALAPPDATA%\RollFlow-V363-Staging` with PostgreSQL port **55435** and
web port **18083**. Use `First Setup.cmd` once in a fresh extracted folder,
then `Start RollFlow.cmd` and open `http://localhost:18083/`.
Do not overwrite V3.5, V3.6.1, or V3.6.2 test instances.

Only use fictional records on a home computer. Real school information
requires a formally approved private school host and access controls.

---

# V3.6.2 — Guided OneSchool Import Centre (development staging)

This build extends the V3.6.1 connected teacher portal with a guided importer at
`/manage/oneschool/documents/`. Its shortcuts use **separate** instance state
`%LOCALAPPDATA%\RollFlow-V362-Staging`, PostgreSQL port **55434**, and local
web port **18082**; existing V3.5 and V3.6.1 installations are untouched.

For a new, empty V3.6.2 test instance, extract the downloaded ZIP to a fresh
folder and run **First Setup.cmd** once, then **Start RollFlow.cmd** and browse
http://localhost:18082/. To start an existing V3.6.2 instance use Start only.
Never delete a previous version's instance directory to troubleshoot setup.

Inside the Admin Portal, navigate to OneSchool Import Centre → **Guided
OneSchool imports & offline archive**. The page explains where to find SM110
Dynamic Student List Excel, whole-staff timetable PDF, and multiple
TTLineAlignmentExport parts. **Only** the Excel student directory/home-group
upsert is currently supported after explicit review. PDF and TTLine sources
are kept in the encrypted archive pending verified field mapping. Subject-class
enrolments remain out of scope.

Archive paths under the *private* state folder:
`oneschool-imports/` (encrypted original blobs),
`oneschool-import.key` (separate Fernet key), and
`uploads/` (temporary private intake area).
The PostgreSQL backup does not include archived files or the key. Always
maintain a suitably protected offline copy of all components, follow retention
rules, and rehearse a restore on a separate test machine. The archive cannot be
restored without its key. Exports must never be placed in GitHub, application
static files or consumer-cloud backup services.

Use **fictional data only** in the home/test installation. This is unsigned,
unapproved staging software: live staff/student information requires school ICT
authorisation, a privacy impact assessment and the approved private environment.

---

# V3.6.1 — Integrated Windows staging (V3.5.1 installation + V3.6 portal)

## Safe side-by-side test on a home computer

Do not overwrite the older, working V3.5 installation or reuse its data directory
for the first V3.6.1 test. Extract the staging artifact into a **new folder**,
such as `C:\RollFlow-V361-Test`. Stop the previous RollFlow process
before testing or use the separate ports shown here. The **corrected
V3.6.1 Windows package** now makes `First Setup.cmd` and `Start RollFlow.cmd`
use a distinct `%LOCALAPPDATA%\RollFlow-V361-Staging` instance and ports
55433 (PostgreSQL) / 18081 (web). You can use those shortcuts directly if the
new state directory does not already exist.

If you already downloaded an earlier V3.6.1 archive whose shortcuts still
point at `%LOCALAPPDATA%\RollFlow-Staging`, **do not delete the existing
directory**: it may hold the working V3.5 test data. Instead, open PowerShell
in the new extracted folder and run the explicit isolated commands below,
or download the updated package.

```powershell
$state = Join-Path $env:LOCALAPPDATA 'RollFlow-V361-Staging'
.\python\python.exe -m deployment.native --state $state init --db-port 55433 --web-port 18081
.\python\python.exe -m deployment.native --state $state start
```

Create a fictional administrator at the prompt. Open http://localhost:18081/.
Stop the new server with Ctrl+C. For subsequent sessions, run the second
command only. This separate state and set of ports mean that the older V3.5
testing database and passwords are not altered.

The personal teacher portal requires a published **fictional** OneSchool
timetable and an administrator-verified matching staff-ID link. Use the
administrative Staff Management edit screen to verify the identity explicitly.
After setup, the teacher can use My day and My week; unverified links fail closed.
The live school profile requires an approved HTTPS gateway and must **not**
be enabled for an unapproved home test. Do not import genuine school information.

The native runner has no automated in-place upgrade or restore procedure.
A clean-machine and isolated backup/restore test are required before
considering a release. This build is unsigned staging software only.

## What is supported in this engineering release

A local PostgreSQL cluster, Django local accounts, Argon2 password hashes, existing student/photo/staff/timetable models, local sessions, static assets and a Waitress WSGI server. No cloud database, subscription or external identity provider is required. Attendance remains unfinished; school mode hides the fictional teacher workspace. No automatic internet downloads at instance setup or runtime. The Windows bundle builder is source code, not a signed or independently verified installer.

## Windows x64 distribution build (release engineer only)

On Windows x64 with full CPython 3.14 and Git, obtain and verify the approved CPython 3.14 x64 embeddable ZIP and the approved PostgreSQL x64 binary distribution; extract each. Use security-supported runtimes and include upstream licence notices and any Microsoft runtime prerequisites. If suitable patched redistributables are not available, qualify another Python version before distribution. Run:

```powershell
python deployment/build_windows.py --python-runtime C:\build\python-embed --postgres-runtime C:\build\pgsql --output C:\build\RollFlow
```

The builder copies the runtimes, fetches binary wheels on the build machine only, installs from the local wheelhouse, checks imports with the bundled Python, and creates a SHA-256 file manifest. The manifest is not a digital signature. GitHub Actions also attempts a Windows x64 staging artifact using the pinned Python 3.14.10 archive checksum and PostgreSQL 18.7 binary archive with the vendor-provided checksum. Only a successful build and native smoke test uploads the artifact. Vendor checksums do not replace independent release signing or security review. Verify upstream distribution licences, provenance, checksums and vulnerability status before releasing or signing any package. The target must have a compatible OS and Microsoft runtime libraries. A full clean-machine test is mandatory; copying the distribution does not establish ICT approval.

## Offline synthetic staging

Copy the built directory to local storage, not a network share or USB for running the database. Run under a standard dedicated account, not Administrator/root. Configure restrictive access (Windows NTFS ACLs) to the application and private data directories. Double-click First Setup.cmd once; create the initial admin at the prompt using a unique password. Start RollFlow.cmd and browse http://localhost:8080/. In this V3.6.1 Windows package, the shortcuts use %LOCALAPPDATA%/RollFlow-V361-Staging, not the native command's legacy default of %LOCALAPPDATA%/RollFlow-Staging. The first setup shortcut also selects ports 55433 and 18081. Ctrl+C stops the application and the database it started. Application files and persistent state are separate. Do not use real records in staging. For a different state directory, call the bundled Python directly with --state before the command. Do not run two launchers against the same instance.

### Windows PostgreSQL initialization permissions (V3.5.1)

First setup now removes inherited NTFS permissions on the new instance directory and
grants access explicitly to the Windows account performing setup. The short-lived
`initial-password.txt` file receives a separate current-user SID grant so
PostgreSQL `initdb` can read it even when its Windows token does not retain
access through the Administrators group. The file is deleted after setup or a
failed `initdb` attempt. ACL changes fail closed; do not work around failures
with `Everyone`, `Users`, or broad administrator-group access. Use a local
NTFS volume and the same dedicated standard account to set up and run RollFlow.
Windows CI covers the bundled `initdb`, migration and backup path; a clean-machine
test is still required before any release.

## Private school profile (future approved pilot only)

```powershell
.\python\python.exe -m deployment.native --state D:\RollFlowData init --mode school --host rollflow.school.example
.\python\python.exe -m deployment.native --state D:\RollFlowData start
```

School mode requires DEBUG off, specific allowed hostname, PostgreSQL, a per-instance random secret, live timetable mode and a trusted HTTPS gateway. The launcher starts PostgreSQL and Waitress on 127.0.0.1 only; ICT must provide internal DNS, TLS certificate, reverse proxy, network ACLs and dedicated least-privilege OS account. The proxy must overwrite forwarded headers (including X-Forwarded-Proto), preserve the approved Host header and be the only allowed HTTP ingress. Do not expose the application port or database port. Restrict local access because loopback is not a boundary against untrusted local users. Use approved encrypted disks and backups. The private state directory contains credentials, including a distinct database-owner credential; protect with restricted ACLs and never share or commit it. Restrict access to the state parent before running initialization. The school HTTPS gateway remains a separate ICT-managed component. Do not run extracts or use actual student information until departmental approval, security testing and operational features are complete.

## Backup and upgrade foundation

Use Backup RollFlow.cmd with a new destination path for staging, or call the bundled interpreter with --state and backup for a named instance. This uses PostgreSQL pg_dump custom format. It does not encrypt the dump; select approved encrypted storage and restrictive permissions. It is a database-only backup: ICT must separately protect the instance configuration, keys and owner credential. Restore drills, automated backup scheduling, Windows service installation, signed releases and rollback-safe upgrades remain future work. Never copy a running PostgreSQL data directory to USB as a backup. Stop application before replacement, take verified backups, test migrations on a separate restored copy; no automated in-place upgrade is supplied.

## Development/CI verification

The existing suite runs on both SQLite and PostgreSQL. The native launcher can be exercised using an installed PostgreSQL binary directory on Linux with --pg-bin; it is not necessary to install Windows runtimes for this test. CI uses fictional data only. A successful CI run demonstrates the checked operations, not live deployment approval.
