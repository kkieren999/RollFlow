# V3.5 — Self-contained School Edition foundation

## What is supported in this engineering release

A local PostgreSQL cluster, Django local accounts, Argon2 password hashes, existing student/photo/staff/timetable models, local sessions, static assets and a Waitress WSGI server. No cloud database, subscription or external identity provider is required. Attendance remains unfinished; school mode hides the fictional teacher workspace. No automatic internet downloads at instance setup or runtime. The Windows bundle builder is source code, not a signed or independently verified installer.

## Windows x64 distribution build (release engineer only)

On Windows x64 with full CPython 3.14 and Git, obtain and verify the approved CPython 3.14 x64 embeddable ZIP and the approved PostgreSQL x64 binary distribution; extract each. Use security-supported runtimes and include upstream licence notices and any Microsoft runtime prerequisites. If suitable patched redistributables are not available, qualify another Python version before distribution. Run:

```powershell
python deployment/build_windows.py --python-runtime C:\build\python-embed --postgres-runtime C:\build\pgsql --output C:\build\RollFlow
```

The builder copies the runtimes, fetches binary wheels on the build machine only, installs from the local wheelhouse, checks imports with the bundled Python, and creates a SHA-256 file manifest. The manifest is not a digital signature. GitHub Actions also attempts a Windows x64 staging artifact using the pinned Python 3.14.10 archive checksum and PostgreSQL 18.7 binary archive with the vendor-provided checksum. Only a successful build and native smoke test uploads the artifact. Vendor checksums do not replace independent release signing or security review. Verify upstream distribution licences, provenance, checksums and vulnerability status before releasing or signing any package. The target must have a compatible OS and Microsoft runtime libraries. A full clean-machine test is mandatory; copying the distribution does not establish ICT approval.

## Offline synthetic staging

Copy the built directory to local storage, not a network share or USB for running the database. Run under a standard dedicated account, not Administrator/root. Configure restrictive access (Windows NTFS ACLs) to the application and private data directories. Double-click First Setup.cmd once; create the initial admin at the prompt using a unique password. Start RollFlow.cmd and browse http://localhost:8080/. The default data directory is %LOCALAPPDATA%/RollFlow-Staging on Windows. Ctrl+C stops the application and the database it started. Application files and persistent state are separate. Do not use real records in staging. For a different state directory, call the bundled Python directly with --state before the command. Do not run two launchers against the same instance.

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
