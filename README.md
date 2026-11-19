# RollFlow — Teacher Edition

## V3.4.1 — Full-size test import and hosted publishing

The public OneSchool Import Centre now supports temporary full-size Test Import (20 MB / 150,000 rows) with masked timetable preview. Only use data your school authorises for local testing. Results are not published or written to localStorage. The public publishing workflow remains fictional. Direct publication of an original school CSV is implemented in the private server version and requires school ICT approval, private HTTPS hosting, PostgreSQL and individual accounts. See the [server branch](https://github.com/kkieren999/RollFlow/tree/v3.0-foundation).

## V3.4 — OneSchool integration and advanced timetable management

Open the public preview with admin / admin, then **OneSchool Import Centre → Load fictional sample**. Review counts/warnings and publish the draft. The Master Timetable changes to the published dated snapshot and the teacher's View planned timetable opens a fictional personal schedule. Try Monday and Tuesday to see different bell times. **Never upload real OneSchool data to the public demo.** Only DEMO-prefixed identifiers and the synthetic names are accepted, with at most 500 rows and five versions. The generated sample has 144 rows across five days. The original staff/student/class management and roll marking workflows remain separate.

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
