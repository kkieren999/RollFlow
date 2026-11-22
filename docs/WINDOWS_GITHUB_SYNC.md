# RollFlow: GitHub / Windows parity and future synchronisation

**Status (23 November 2026): preparatory; not an automatic two-way updater.**

## What the two versions currently are

- GitHub \`main\`: the V3.4.4 **public, browser-only** Pages demonstration. Its local browser storage is not the Windows school database.
- \`feature/v3.6.7-unified-ui\`: newer **Django / PostgreSQL / offline Windows** engineering staging source. Its GitHub Actions workflow builds a Windows x64 staging bundle and performs synthetic-data tests. It is still in a chain of draft pull requests and has not been merged into \`main\`.
- A Windows installation consists of an extracted build containing \`app/\`, \`python/\` and \`postgres/\`, plus a separate private state folder. It does **not** contain a Git working copy. Saving a file in that installed \`app/\` folder will not send it back to GitHub.
- No one can establish that the installed Windows bundle matches a given GitHub commit without examining the Windows app files or trustworthy build provenance.

These editions are not interchangeable. GitHub Pages cannot host Django, PostgreSQL, private authentication, or the connected school database.

## 1. Read-only Windows comparison

A diagnostic is available at \`deployment/compare_windows_bundle.ps1\` in the parity-check branch. From Windows PowerShell:

\`\`\`powershell
powershell.exe -NoProfile -File .\deployment\compare_windows_bundle.ps1 -InstallPath 'C:\Path\To\Extracted\RollFlow' -ReportPath '.\rollflow-version-report.json'
\`\`\`

Use the **folder containing \`app\`**, not \`%LOCALAPPDATA%\RollFlow-V3641-Staging\` or the PostgreSQL data folder. Alternatively, pass a RollFlow source folder containing \`index.html\` directly. The script defaults to comparing against \`feature/v3.6.7-unified-ui\`; change \`-Branch\` to compare a different commit lineage.

The tool fetches GitHub's public Git tree and computes Git-blob hashes for *tracked app source files only*. It prints counts and names of missing/different files, and can write a JSON report. It **does not edit files**, **does not inspect school databases, student content, OneSchool imports, passwords, keys, backups, browser data or logs**, and **does not upload local content**. It needs internet access; do not run it against a restricted host contrary to school ICT rules. It does not inspect untracked files or prove application/DB compatibility.

If Windows PowerShell blocks execution, follow the organisation's script execution policy; do not disable a school security control just to run a diagnostic.

## 2. A safe code-sync model

Choose one **canonical development branch** after resolving the draft PR chain and confirming the installed bundle's source. Keep GitHub Pages demo publishing separate from server builds.

For **editing RollFlow code on Windows**, work in a Git clone, *not* in the installed offline bundle:

\`\`\`powershell
git clone https://github.com/kkieren999/RollFlow.git
cd RollFlow
git switch feature/v3.6.7-unified-ui
git pull --ff-only
# Make and test code changes here; then:
git add -- <specific-source-paths>
git commit -m "Describe the code change"
git push origin feature/v3.6.7-unified-ui
\`\`\`

Only add reviewed source files. Do not run \`git add .\` against a folder containing private school data. Do not commit or push real OneSchool exports, instance configuration, credentials or database files.

For **editing the source on GitHub**, make the changes on the same source branch (preferably through a PR). CI can then build a new **versioned Windows artifact** from that commit. A Git commit or successful CI run does not automatically replace an already-installed bundle.

To keep multiple *Git source checkouts* current, perform \`git fetch\` / \`git pull --ff-only\` before changing files, and \`git push\` after committing. Git can report conflicts that require a deliberate human merge; silent last-writer-wins two-way mirroring of source code is unsafe.

## 3. Updating the already-installed Windows program

For **the existing V3.6.4.x / V3.6.5 / V3.6.6 staging family** only, the repository's \`deployment/README.md\` documents a backup-first upgrade:

1. Identify the installed bundle **and** private state path. Check source parity first. Verify that the intended replacement build is newer, from a trusted commit, and is compatible with that instance.
2. Stop RollFlow **and PostgreSQL**, retain the old extracted bundle, keep the PostgreSQL runtime directory unchanged and preserve all private state.
3. Download an appropriate CI staging artifact (available for limited retention) to a **new, separate** extracted code directory. Do not overwrite the existing directory.
4. Run that version's \`Upgrade Existing.cmd\`, which is intended to back up the PostgreSQL DB, encrypted OneSchool archive and key before migrations. Verify that the upgrade succeeds.
5. Run \`Start RollFlow.cmd\` and regression-check the teacher and administrator views with authorised *fictional test data*.

**Never run \`First Setup.cmd\` over an existing state folder.** Do not substitute a generic \`git pull\` for an installed-bundle upgrade. Test backups and restore procedures before adopting any updater.

The staging bundle is not signed or approved for real school use. Automatic in-place updates are **not enabled** and should not be enabled until signed releases, checksum/provenance verification, compatibility gates, backups, rollback, and school ICT/security approval exist.

## 4. Synchronising working data (not source code)

Windows RollFlow school data currently live in its **private local PostgreSQL instance**; public GitHub Pages data live in each browser's local storage. They are not the same dataset, and uploading the local DB to GitHub would be unsafe.

If the goal is that entering attendance, students, teachers, or timetables on one device immediately appears on another, the appropriate solution is **one school-approved, access-controlled central server and database**, with proper authentication, HTTPS, permissions, audited changes, secure backup, offline-conflict handling (if offline entry is required), and an approved privacy/retention policy. GitHub should only distribute reviewed code, never identifiable school data.

## 5. Engineering tasks required before automatic updates

1. Confirm the actual Windows installation's app hash report, bundle version, state location and upgrade history.
2. Rationalise the V3.6.x draft PR chain, test and nominate one release source branch. Keep the V3.4.4 Pages demo separate or explicitly redesign its public deployment.
3. Add immutable release IDs and verified build provenance to Windows artifacts, then signed/tagged releases and a publish pipeline.
4. Add an updater that **checks, downloads, verifies and stages** a release and asks for an approved maintenance window. It must refuse to replace a running DB or apply unknown schema migrations, automatically back up, and support rollback.
5. If truly automatic *data* synchronisation is requested, design a private online service; do not route school records through GitHub.

**Bottom line:** code can use GitHub as its source of truth, and GitHub Actions can build Windows bundles from the same code. The existing Windows installation and GitHub Pages are not automatically bidirectionally synchronised today. The parity report is the first safe step toward verifying and reconciling them.
