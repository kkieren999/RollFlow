# RollFlow V3.0 — School application foundation

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
