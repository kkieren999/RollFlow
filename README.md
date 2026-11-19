# RollFlow V3.0 — School application foundation

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

Choose a unique administrator username and strong password at the prompts. Open http://127.0.0.1:8000/ and select the Admin login cog. The administrator overview is Django's database-backed administration interface. Under Users, add a fictional teacher with a strong password, first and last name; on the user's change page ensure Active is checked, Staff and Superuser are unchecked, and assign the Teacher group. Add an optional Staff Profile to set faculty, campus and staff ID. Sign out, then sign in through the teacher login. Account names are assigned by the administrator, not editable in the teacher workspace. Disable accounts instead of deleting them.

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
