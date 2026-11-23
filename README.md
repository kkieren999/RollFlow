# RollFlow — Teacher Edition

## Public Pages teacher demonstration login: swilliams

The **public browser-only demonstration** now accepts `swilliams / swilliams` in addition to `teacher / teacher` and `admin / admin`. The fictional Sarah Williams account has the existing timetable fixture classes `ENG071A` (Year 7 English), `ENG091B` (Year 9 English), `ENG101B` (Year 10 English) and `10BH` (Year 10B Home Group).

The two teacher demos have separate **browser-local** attendance and workspace storage keys. Signing out of Sarah Williams returns to the public login, and changing teacher reloads the demo identity to avoid sharing in-memory teacher state. This is **not real authentication**; credentials are public and any browser user can enter either identity. School planning preview and other shared fictional fixture data remain browser-local. No real school or Windows user credentials and no private PostgreSQL records are involved. GitHub Pages cannot log into or synchronise with a Windows school database.

### Recorded service visits automatically appear in the student day template

When a student is issued a pass to Toilet, Student services, School office,
Library, or another administrator-configured service in the fictional demo,
that pass is written to the existing movement log and the student's
**Care class–Period 4** day template automatically. The effective pass-writing
function now records the Brisbane departure time and the session it belongs
to; older passes are grouped using their recorded time. The template shows
the **service name, time out, return status and (when available) duration**.
Marking a pass returned also updates its template entry. No periods are
filled unless a matching service visit exists on the selected date.

Teachers can click **View in template** on any row of Movement log to select
that student and the actual date of the visit, or search by name/ID below
the log. Shortcut chips show students with visits on the selected date,
including the count. A student with no visits still has empty Care/Period
cells; outside-period visits remain visible in a separate list.

This applies to browser-local fictional demonstration records; it neither
creates student attendance marks nor imports school data. It is not a
secure cross-browser movement register or a live Windows school database.

### Searchable movement timeline — Care class through Period 4

Below **Movement log**, teachers can search the fictional student directory by
name or ID and select a student. A read-only **Student movements by period**
table shows movement departure and return details for the selected calendar
date, grouped by the time the pass was issued. The five rows are **Care class
(8:35–8:50 am)**, **Period 1 (9:00–10:10 am)**, **Period 2 (10:15–11:25 am)**,
**Period 3 (11:30 am–12:40 pm)** and **Period 4 (1:20–2:30 pm)**. Rows
without movements are left **empty**, and multiple movements within one period
are retained. Movements outside these time windows are shown separately rather
than dropped. Changing the date in the green Student Movements header updates
this view; it does not display outstanding passes from other dates.

The table uses only existing fictional demo records and browser-issued passes,
does not invent visits or attendance marks, and does not alter pass actions or
student records. This website feature is browser-local, not a centrally
authorised student movement register, and does not install itself onto Windows.

### Administrator-managed Student Movement destinations (fictional demo)

On the GitHub Pages demonstration, sign in as `admin / admin` and open
**Student Movements → Manage movement destinations**. Administrators can
add unique destinations (2–50 characters, maximum 30) and remove any
destination except the final remaining one. New student passes issued
from the teacher demo use this list instead of hardcoded choices. A
removed destination is no longer available for **new** passes, but
existing browser-issued passes and historical sample visits retain their
original destination names in movement logs and student-history filters.

The settings are saved separately under
`rollflow_demo_movement_destinations_v1` in browser localStorage, so all
demo identities in **the same browser** see the same list. Other browsers,
machines, and the installed Windows app are **not synchronised**.
The public `admin / admin` account is a fictional interface and **not
secure administrator authorisation**. Never record real school movements
or assume these browser-local settings are centrally enforced.

### Student Movements — Example 1 dashboard

The public GitHub Pages demo now uses the compact green **Student Movements**
dashboard: Currently out / Returned / Total passes counters, the existing
student search and destination selector, **Issue pass**, and a dated movement
log with student photos, duration, status, **Mark returned** and an
All / Currently out / Returned filter. It keeps demo movement records in
browser localStorage and preserves the original live-pass validation.
Past dates are for review only, not issuing new live passes.

This is **fictional demo UI**, not a production movement register. The
installed Windows app is a separate build and does **not** automatically
update when GitHub Pages is published. The V3.6.7 Windows staging branch
has a corresponding update to its bundled offline demo; its connected-school
Django timetable uses a separate interface and requires an approved Windows
build and manual upgrade. No browser movement records or credentials
synchronise between machines. Do not enter real school records.

**Example movement data (fictional):** The older auto-generated counts (6–10 visits for *every* student) have been replaced by a smaller set of completed demonstration visits for 18 selected fictional students. Four have frequent visits (10–15), six have occasional visits (3–6), and eight have just 1–2; other students have no generated history. The dates cover past 2026 school days, with a few completed examples on the latest school day. Their records appear in the normal movement log, clearly marked **Fictional sample**, and in Student Finder's movement history. No sample is an active pass. Existing passes issued in this browser remain unchanged; recognisable legacy auto-generated samples are migrated once, while custom sample history is preserved. The redundant **Daily Service Usage**, **Students Using Each Service** and **Visits to Each Service** panels have been removed from Student Movements. New passes remain browser-only and do not sync to Windows.

### Sarah Williams's fictional 2026 timetable

The browser demo generates Sarah Williams's schedule **for any selected 2026 school date**, including past school dates. It is a *fictional weekly template*, not a copy of OneSchool or a timetable synced from Windows. It repeats throughout the Queensland term dates below; there is no data upload or migration. The existing Sarah-specific local attendance and preferences are retained.

| Day | Home group 8:35–8:50 | P1 9:00–10:10 | P2 10:15–11:25 | P3 11:30–12:40 | P4 1:20–2:30 | P5 2:35–3:10 |
|---|---|---|---|---|---|---|
| Mon | 10BH · G05 | ENG071A · B14 | ENG081C · B17 | ENG091B · B14 | ENG101B · B13 | Spare |
| Tue | 10BH · G05 | ENG101C · B18 | ENG071A · B14 | ENG081C · B17 | Spare | ENG091B · B14 |
| Wed | 10BH · G05 | ENG091B · B14 | ENG101B · B13 | ENG101C · B18 | ENG081C · B17 | Spare |
| Thu | 10BH · G05 | ENG101B · B13 | ENG091B · B14 | Spare | ENG071A · B14 | ENG101C · B18 |
| Fri | 10BH · G05 | ENG081C · B17 | ENG101C · B18 | ENG071A · B14 | ENG101B · B13 | Spare |

Classes are Year 7 (\`ENG071A\`), Year 8 (\`ENG081C\`), Year 9 (\`ENG091B\`), Year 10 (\`ENG101B\` and \`ENG101C\`), and Year 10B home group (\`10BH\`). Each English class meets on four separate weekdays; no periods overlap. Spare periods appear in **My Timetable**, but have no roll to submit.

**Queensland 2026 state school terms (student dates):** 27 Jan–2 Apr, 20 Apr–26 Jun, 13 Jul–18 Sep and 6 Oct–11 Dec (see [Department of Education](https://education.qld.gov.au/about-us/calendar/term-dates)). Saturdays, Sundays, term holidays, the statewide Labour Day holiday (4 May), Brisbane's Ekka show holiday (12 Aug) and the student-free development day (4 Sep) have no scheduled lessons. Year 10 student lessons and the Year 10B home group end after **27 November 2026**; Years 7–9 lessons continue until **11 December**. The timetable is deliberately scoped to 2026, not a real school's roster.

**Teacher page navigation:** The Take Attendance page now has a clearly labeled **Back to Daily Schedule** button (which preserves the selected date), a prominent class-code/subject heading, and clearly grouped period/time/room details. The classroom picker displays the selected date's timetable, and Class Finder's detail page shows Sarah's repeating weekly periods. Past-due attendance displays the shorter label **Roll overdue**.

## V3.4.4 — Import reliability and timetable bug fixes

Browser import fingerprints are based on the original decoded CSV content, not masked timetable structure. Only the fingerprint and masked schedule are stored. Exact repeated source text reuses a version; changed source text (including row order or duplicate rows) creates a new version. Existing V3.4.2/3 versions remain intact; the first reimport under V3.4.4 may create a new version. The original file is not stored or uploaded. Use approved data only; masking is not a guarantee of anonymity.

Strict quote validation, safe date bounds (1900–2099), correct visible allocation counts, staff selection in the staff timetable, filter reset on view switching, and expiry warnings are included. Committed changes notify other open tabs in the same browser/origin; focus/visibility reloads reconcile missed notifications. In-progress imports defer refreshes. Publish a replacement before deleting any active version. Date sorting and keyboard focus have been improved. This is still a local masked timetable and not an operational attendance system.

Focused synthetic regression checks passed for both branch previews; the supplied CSV passed equivalent local structural validation (42,793 rows). Actual browser multi-tab/device testing remains unverified. The protected Django branch passed all 42 `accounts` regression tests, dependency installation, system checks and migration validation in [GitHub Actions run 44614590326](https://github.com/kkieren999/RollFlow/actions/runs/44614590326) on 20 November 2026 (Brisbane time), using development SQLite. [GitHub Pages deployment run 44614578637](https://github.com/kkieren999/RollFlow/actions/runs/44614578637) also succeeded for the static preview; independent browser testing and a private Django/PostgreSQL production deployment remain unverified.

## V3.4.3 — Usability and stability

Dashboard metrics reflect the published local imported timetable. Master Timetable now supports previous/next week, Today, first imported day, live search, year/staff/room filtering, click-to-lookup aliases, highlighted matches, expand/collapse, compact and expanded viewing, and current bell-period indicators in Brisbane time. Management tables support local sorting, live table search and 25/50/100-row pages; selected management tabs and compact/highlight preferences are remembered. The browser edition remains masked and local; attendance and individual accounts are not linked.

## V3.4.2 — Timetable publication

Open **OneSchool Import Centre** and import the original 15-column CSV (up to 20 MB / 150,000 rows). Enter a version name, confirm authorised use and replacement, and click **Import & publish timetable**. The browser edition validates and masks class, staff and room identifiers and nonstandard period labels before saving a persistent version in IndexedDB. It does not upload the CSV or save the original identities, names, subjects or MISIDs. The dates and bell times are retained. This is a local masked timetable, not a shared school database or full anonymisation guarantee. Use only data approved for this purpose. Previous versions can be reviewed, republished or removed. The former temporary import and sample publishing controls have been removed.

The Master Timetable uses the active local import and the staff timetable filter uses masked aliases; staff-account mapping and attendance remain separate. Individual accounts, original identifiers and school-wide data sharing require the [protected server installation](https://github.com/kkieren999/RollFlow/tree/v3.0-foundation). GitHub Pages cannot host the application server.

## V3.4 — OneSchool integration and advanced timetable management

Superseded by the V3.4.2 persistent masked import workflow above. The original fictional attendance fixtures remain separate from imported planning.

Timetable Management now has Overview, Lesson allocations, School periods, Rooms, Versions and Import tabs. The Versions and Import tabs link to the same review/import workflow. Manual periods and slots are separate from imported date-specific periods and allocations; publishing replaces the full imported snapshot, including its date coverage, without changing manual records.

See the [V3 development branch](https://github.com/kkieren999/RollFlow/tree/v3.0-foundation) for the full-size server importer and setup instructions.

## V3.3.1 — Master Timetable

Open **Master Timetable** immediately below My Timetable (teacher) or Timetable Management (administrator). The school-wide grid is generated from the existing fictional planning records, with weekday tabs, period columns, expandable Years 7–12, class/teacher/room search, year filtering, class details, clash flags, free-resource counts and printing. The default day is the current Brisbane weekday, or Monday on weekends. Break columns can be hidden when their period names contain Break, Recess, Lunch or Interval. Removed periods and inactive allocations are excluded. Counts are based on the full day's known active planning resources, not filtered search results.

Administrators can open a class or edit a lesson from its details. Teachers can pin a matching fictional attendance fixture as today's supervision only when the selected lesson matches today's fixture day, period and room; other planning records remain read-only. The browser-local planning preview is separate from attendance. No real school timetable data is included.

## V3.3 — Class & Timetable Management preview

Sign in with admin / admin and open Class Management or Timetable Management. The fictional planning directory starts with 34 classes and 34 recurring lesson slots. Create/edit classes, select a primary teacher, manage dated student enrolments, schedule lessons, manage rooms and periods, archive slots, and import timetable CSV. Existing sample teachers without a matching staff account retain their fixture display names. New allocations require an active fictional teacher account. Teacher / teacher can view the automatically filtered planning timetable under My Timetable → View planned timetable.

CSV header: `class_code,teacher_username,room_code,weekday,period_code`. Weekdays use 1–5. All references must already exist; conflicting teacher/class/room slots are rejected. Import up to 500 rows below 250 KB. New entries are checked for clashes; original fixture inconsistencies are not silently rewritten. School periods seed the existing RollFlow schedule. No term calendars, student-level clashes, or actual roll records are managed by this release.

Public planning data is browser-local and strictly fictional. Roll marking still reads the original fixture data, separate from planning changes. The database-backed version is on the [V3 development branch](https://github.com/kkieren999/RollFlow/tree/v3.0-foundation).

## V3.2 — Student Management preview

Sign in with the public admin / admin demonstration account and select Student Management. The directory starts with 240 fictional fixture students. Search by name or ID, filter by year, home group or enrolment status, add or edit student records, view profiles, toggle synthetic portraits and import a fictional CSV. Student IDs are stable; leaving dates are required when marking a student as left. Records are kept rather than deleted.

The demo uses synthetic illustrations only. Do not upload or enter real student information. Student changes are stored in this browser and do not update the Teacher Portal's fixture rosters. Existing fixture home groups and class memberships are illustrative; only unambiguous fixture home groups are prefilled. Actual class allocation comes in V3.3.

CSV header: `student_id,first_name,last_name,preferred_name,year_level,home_group,status,enrolled_on,left_on`. Use years 7–12, active/inactive/left status and ISO dates (YYYY-MM-DD). Import up to 500 rows, 250 KB, with duplicate checking. Download the template from Student Management → Import CSV. The server version is on the [V3 development branch](https://github.com/kkieren999/RollFlow/tree/v3.0-foundation).

## V3.1 — Administration Portal preview

Select the settings cog on the public login screen and enter `admin / admin`. The admin dashboard and permanent navigation include staff management, local activity, CSV import and role descriptions. Other school-management modules are labelled as planned.

Staff directory changes (add, edit, activate/deactivate, draft class allocations and simulated password resets) persist only in this browser. Fixed demo logins remain protected and additional fictional records do not create working logins. CSV imports use the exact UTF-8 header `staff_id,username,first_name,last_name,faculty,campus` and create inactive fictional teacher records. No passwords are stored by the preview. The teacher login remains `teacher / teacher`.

For the database-backed staff interface, see the [V3 development branch](https://github.com/kkieren999/RollFlow/tree/v3.0-foundation). Never enter real staff or student information into this demonstration.

## V3 — Demo sign-in preview

The public GitHub Pages demonstration now opens with a sign-in page. Use **teacher / teacher** for the Teacher Portal, or select the settings cog and use **admin / admin** for the separate administrator overview. Sign out to switch accounts. A tab-local session flag is stored in sessionStorage; existing fictional records remain in localStorage.

These fixed, publicly visible credentials are UI demonstrations only, not real authentication or authorisation. The administrator overview is a starting page, not a functioning staff-management system. Never enter actual school passwords or personal information. Production requires a school-approved backend, secure sessions, server-enforced permissions and central storage outside GitHub.

## V2.1 — Teacher Experience & Reliability

RollFlow is a single-page, browser-based teacher attendance demonstration designed around a Queensland teaching day. All information is fictional.

### Everyday teacher workflow

- Select the **RollFlow logo** to return to today's schedule. Home is no longer a separate sidebar item.
- **My Timetable** provides day and week views, using the same date-aware schedule as the daily overview. The supplied assigned-class example data defines Wednesday lessons only; other weekdays have no invented lessons. Temporary cover plans and today's pinned supervisions appear on their applicable dates.
- Unsubmitted scheduled rolls receive a red outline 10 minutes after their lesson begins, using Australia/Brisbane time. Submission removes the overdue outline.
- **Take Attendance** uses a minimal student photo grid (30 photo controls for the example Mathematics class). Tap a photo to cycle `? → P (Present) → A (Absent) → L (Late) → ?`. Letter and outline indicate the status. Activity is not a new marking option; legacy records are retained.
- The attendance class dropdown contains assigned classes and supervision classes pinned today. Other fictional classes can be reached through Class Finder.
- Undo, Save, mandatory confirmation and submission are retained. A receipt summarises the submitted roll. Browser-storage errors produce a warning and a retry action rather than reporting successful submission.
- Submitted scheduled rolls can be corrected by opening a student's details, choosing a new attendance status and supplying a reason. The roll stays submitted and the correction is logged locally. Attendance History under School Tools also supports reviewing submitted rolls, CSV export, and reason-required reopening of a roll.

### Students and movements

- **My Classes** lists assigned teaching groups; **Class Finder** searches the directory of 34 fictional classes across Years 7–12. View class details, rosters, sample timetables and attendance.
- **Student Search** and the student details panel link to the student's own sample class memberships, timetable, submitted attendance history, movement history and attendance comments.
- Tap a student's name, right-click their portrait or long-press a portrait to open details without navigating away from the roll.
- Movement passes prevent a second active pass for the same student. New passes record departure and return timestamps and calculate elapsed minutes; old records without timestamps show duration not recorded. Active passes remain visible until returned.
- **My Cover Plan** records sample relief allocations, temporary timetable changes, supervision and handover notes.

### Profile and preferences

My Profile presents the teacher's details in a clean view, with an explicit Edit Profile action. My Preferences has 11 settings grouped under Appearance & accessibility, Teaching & attendance, and Reminders & notices. Submission confirmation, totals, overdue indicators, stable student positions and today's initial date are automatic. The day/week selector lives in My Timetable. Preferences are saved in this browser; resetting them does not remove attendance, notes, favourites or cover plans.

Earlier workspace data (favourites, recent history, teaching notes and links) is preserved. The simplified sidebar does not expose all of those optional tools. There is no global Search portal button. Help & Support explains the current workflow.

## Run locally

Open `index.html` in a modern browser. There are no dependencies or build commands.

## Host on GitHub Pages

1. Push `index.html`, `.nojekyll` and this README to the root of the `main` branch.
2. Open repository **Settings → Pages**.
3. Under **Build and deployment**, choose **Deploy from a branch**.
4. Choose branch **main** and folder **/(root)**, then Save.
5. Once published, GitHub shows the website link in the Pages section.

## Pin for Today — manual supervisions

From Class Finder → Class Details or Take Attendance, select Pin for Today on a class not already assigned to you. Pinned classes appear on the daily schedule and My Timetable. Pins are bound to the current Australia/Brisbane date, invalidated after midnight and do not change the permanent timetable. A manually entered cover plan can specify a date and period instead.

## Security and product status

**Demonstration only.** The attendance and workspace stores remain browser-local (`rollflow_teacher_2026_v1` and `rollflow_workspace_v2`). Local history is not a secure or tamper-resistant audit trail. There is no staff authentication, secure database, OneSchool integration, SMS delivery or school data transfer. There is no real school authorisation for class access or attendance corrections. Do not use RollFlow for genuine student attendance, live school records or sensitive personal information.

Before a real deployment, implement authorised staff access, server-side class and relief permissions, validated timetable data, secure storage and synchronisation, a durable audit trail, backups and privacy/security review. Do not add real student data or private keys to this public demonstration.

## Verification checklist

Test photo marking, Undo, Save, certification and correction; date navigation and overdue highlighting; pinned and planned cover; student-specific timetables; duplicate movement passes and elapsed durations; persistence and storage errors; dark mode, keyboard navigation and responsive layouts. Logic and rendering checks do not replace testing in real browsers and on school devices.
