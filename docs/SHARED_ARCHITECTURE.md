# Shared architecture — phase 1

## Source and release boundaries
- Proposed canonical branch: main after review and successful CI. Candidate: integration/shared-core.
- Public website and Windows training launcher read the same root index.html and shared assets; no maintained duplicate training tree.
- Protected Django application: accounts/, rollflow/, templates/. Private state, exports and secrets never belong in Git.
- legacy/index.html remains the authenticated fictional fallback used only when no live timetable/publication is enabled. It is not the shared operational interface.
- Build Windows from a reviewed immutable commit; use backup-first upgrades.

## First vertical slice
shared/schedule-core.js validates a versioned schedule DTO, projects only approved presentation fields, and renders common lesson identity. Existing demo teacher and staff schedule routes pass already-scoped fictional rows to the training adapter. The protected connected teacher schedule uses server-side personal_codes and visible_slots to create an authenticated JSON projection. Native cards consume the same renderer, with server HTML fallback. No new client permission decisions or operational writes.

Contract v1: {version:1,days:[{date:ISO,lessons:[{date,code,title,period,time,room,assignment}]}]}. No staff IDs, student IDs, credentials, arbitrary HTML, or permission flags. Every provider must authorize before projection.

## Definition of done
One shared presentation component and contract; fixture and authenticated adapters; explicit server permission checks; no live use of demo storage; accessibility and responsive browser regression; database migration and concurrency tests for writes; versioned build and upgrade tests. Do not duplicate modules per job title.

## Next slices
Unify navigation, personal settings and class detail; replace role gates with granular permissions; create server-authorized attendance model, transaction and audit; then movements and relief. Retire the legacy fallback only after functional replacement and tests.

## Release gates
The historical Windows PR chain is included by the integration commit's second parent; review/close superseded drafts rather than blindly merging. The older consistency audit PR is divergent; review unmerged changes separately. The new deployment/build_pages.py and pages-publish.yml build and publish only files in deployment/public_assets.py (the same allowlist used by Windows training). Before promoting main, switch repository Settings → Pages → Source to GitHub Actions and verify the Pages deployment. The existing branch-root publishing setting could expose legacy/server source paths; do not merge until that gate is resolved. No school data used.

## Baseline browser regression audit
The current main commit bbb40b56b2d6c70b660ff894d59db8b7cb250298 already failed two public browser regressions (run 45758680306): the Principal compact menu count (11 vs expected 10) and an obsolete incident form type selector. The initial shared integration run 45760412576 reproduces both failures. Do not suppress or weaken these checks to release. Reconcile the intended permission/navigation inventory and the simplified classroom action/referral workflow; run the full suite again. A dedicated shared schedule browser smoke isolates the new vertical slice from these pre-existing failures.

## Phase 1B regression repair and promotion

The permission-filtered route inventory replaces stale menu counts with explicit expected primary routes for all thirteen accounts. Class Finder and Classroom Management remain standalone; removed Seating Plans and Class Lists routes are deliberately excluded from visible navigation. Custom incidents retain configured type and response fields, and their class selection and submission are checked against the permitted classroom scope. Built-in late, uniform, departure and truancy actions continue to use their simplified forms; referrals use a separate support action.

The Pages publishing workflow now queries the repository's actual build_type using read-only Pages access and fails its publishing-boundary gate unless the source is GitHub Actions. It builds the allowlisted artifact independently on the integration branch; it never deploys from the integration branch or a pull request. Promote PR #33 only after both browser and server/Windows checks pass and this configuration gate passes. Do not bypass the gate or use a token in source code.

The Pages source configuration was switched by the repository owner and the publishing-boundary check passed on rerun 45761375423. The former animation regression was superseded by intentional weekly grid hardening (41bd56588); the browser test now checks immediate lossless lesson transitions, unchanged identity and reduced-motion behavior. Full suite must still pass before promotion.
