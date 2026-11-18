# RollFlow — Teacher Edition

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
