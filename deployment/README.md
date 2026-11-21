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
