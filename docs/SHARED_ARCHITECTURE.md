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
The historical Windows PR chain is included by the integration commit's second parent; review/close superseded drafts rather than blindly merging. The older consistency audit PR is divergent; review unmerged changes separately. Before promoting main, ensure Pages publishes only public allowlisted artifacts, not legacy fallback or server routes. No school data used.
