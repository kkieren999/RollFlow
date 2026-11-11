# RollFlow — Teacher Edition

A single-page, browser-based teacher attendance demo designed for Queensland schools.

## What is included

- PaperCut-inspired navy-and-green sidebar, with Home, My Timetable, Mark Attendance, My Classes, **Class Finder**, Student Search, Student Movements, and Alerts & Notices.
- My Preferences and Help & Support, plus teacher profile controls.
- Portrait-style synthetic student images, with 30 students visible in the desktop attendance view.
- Student status click cycle: `? → Present → Absent → ?`.
- Student options, Late / Activity selection, notes, movement passes, attendance counts, Undo, and roll submission.
- Desktop, laptop, and phone layouts.

## School-wide Class Finder

The **Class Finder** sidebar page demonstrates a school-wide directory of 34 fictional classes across Years 7–12. Teachers can filter by class code, subject/faculty, year level, day, period, teacher, room and class type. Results open a class details page with portrait student roster, timetable and roll attendance summary. **Mark roll** opens the existing photograph-based attendance screen, including individual marking, Late / Activity, Undo, Save and Submit. On phones, each search result has visible View class and Mark roll buttons.

**Important:** All 34 classes are markable in this frontend demonstration. A production deployment must authenticate staff and enforce server-side class permissions, including relief-teacher assignments. This frontend must not be used to mark or store genuine student attendance.

## Run locally

Open `index.html` in a modern browser. There are no dependencies or build commands.

## Host on GitHub Pages

1. Push `index.html`, `.nojekyll` and this README to the root of the `main` branch.
2. Open repository **Settings → Pages**.
3. Under **Build and deployment**, choose **Deploy from a branch**.
4. Choose branch **main** and folder **/(root)**, then **Save**.
5. Once published, GitHub shows the website link in the Pages section.

Any further commits to `main` will publish updated versions. GitHub Pages is publicly accessible, even for eligible private-repo publishing, so never deploy real student information or secrets.

## Security and product status

**Demonstration only.** All students, portraits and school details are fictional. State is kept in local browser storage. There is no staff authentication, secure database, OneSchool integration, SMS delivery, or school data transfer. Do not use for real student attendance or live school records.

Do not add real student data or private keys to this repository.