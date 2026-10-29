# Implementation verification — local source export

Export of approved source commit `27f292aee03d789cdb36e320f4af2225004db18a`, saved Site version 3. No deployment was made and no UI source was rewritten.

## Results

| Area | Status | Evidence and limits |
|---|---|---|
| Exact source provenance | Passed | Saved-version metadata reports the same commit as the available clean checkout. src, public, original configs/lockfile and tests compare byte-for-byte; see SOURCE_PROVENANCE.json. |
| Fresh dependency installation | Passed | Clean export: `npm ci --no-audit --no-fund` installed 77 packages. The initial offline attempt failed because yallist was not cached; normal installation succeeded. |
| TypeScript | Passed | `npm run typecheck` exited 0. |
| Automated tests | Passed | `npm test` exited 0; 12 tests passed, 0 failed. |
| Production build | Passed | `npm run build` exited 0; Vite/TypeScript built dist. |
| Lint | Not Tested | No lint configuration or script exists in the original project. |
| Local dev server | Passed | Exported project served through Vite and opened in a browser. Local Insights rendered without a backend or the original hosted domain. |
| Homepage | Partially Verified | Local landing rendered with correct existing heading and no broken loaded images. Original source/asset equality passed; authenticated live screenshot comparison unavailable. |
| Insights | Partially Verified | Three editorial sections, current workspace counts, navigation and actual links rendered. Original source equality passed. Hosted page required sign-in, so no pixel-diff to its authenticated rendering. |
| Other discovered routes | Partially Verified | 38 direct local URL/step smoke checks rendered expected headings without the application error boundary. This does not cover every possible form/modal state. |
| Navigation | Passed | Local direct routes, not-found recovery and mobile navigation opening were exercised. Earlier implementation QA covered end-to-end contextual stage navigation; original handlers are unchanged. |
| All interactive component states | Partially Verified | Export retains every original handler. Current export checks include mobile drawer and route rendering. Earlier implementation QA covered guided setup, output import, source inspection/filter/zoom/comparison, council/transcript, ratings, disagreement and reviewed save. Not every modal was retested in this export run. |
| Dark theme | Passed | Source equality and local screenshots preserve the approved dark palette. No theme switch or light theme added. |
| Branding/assets | Passed | All original tracked public files exported; local public/domain route checks reported zero broken loaded images. Asset hashes listed in ASSETS.csv. Font dependencies installed locally. |
| Responsive Insights | Passed | Exact iframe viewports 1440×900, 1366×768, 768×1024, 390×844 were rendered and visually inspected. Body width equalled scrollWidth at each check: 1440, 1351, 753, 375 CSS px respectively; narrower body width reflects the vertical scrollbar. |
| All routes at all viewports | Not Tested | Responsive source is unchanged; only Insights was checked at all four target sizes in this run. Earlier QA checked 390px council and domain gallery. |
| Accessibility | Partially Verified | Existing labelled controls, native dialogs, focus CSS, transcript/source alternatives and reduced-motion rules preserved. Mobile drawer operated. No formal screen-reader audit or exhaustive keyboard test performed. |
| Export download delivery | Partially Verified | Serialization is tested; UI download controls preserved. Browser automation previously did not observe the blob-download event, so end-to-end file delivery is not claimed. |
| Backend integrations | Passed | Boundary documented accurately: no live AI, retrieval, server auth/database or cross-device sync. Imported actual outputs and local/manual evaluation remain available. |
| Windows 11 / PowerShell execution | Not Tested | Instructions supplied. Commands executed here on Linux with Node 24.22.1/npm 11.9.0, not on a Windows machine. |
| Authenticated live-to-local pixel comparison | Not Tested | Deployed /insights returned the ChatGPT sign-in gate. No bypass or UI reconstruction was attempted. Source identity, not an invented pixel-perfect claim, is the fidelity guarantee. |
| ZIP completeness | Passed | Archive created from original files plus local docs; ZIP CRC and extracted source equality checked. node_modules/builds/caches/credentials excluded. |

## Local route smoke list

`/`, `/domains`, six `/domains/{grantha,nyaya,arogya,artha,nivesh,gati}` pages, `/illustrated-overview`, `/research`, `/insights`, `/new-decision`, its `?step=1`, `?step=2`, `?step=3` views, `/decision/research`, `/decision/council`, `/decision/evaluate`, `/decision/consensus`, `/decision/final`, `/library`, `/research/explore`, `/confirm-domain`, `/setup/artha`, `/setup/custom`, `/setup/multi?mode=advanced`, `/review`, `/progress`, `/results`, `/results/evidence`, `/results/perspectives`, `/followup`, `/graph`, `/settings`, `/signin`, `/signup`, `/research-error` and one unknown-route fallback.

## Automated coverage

Domain defaults; context changes; immutable saved snapshots; keyword suggestions; invalid core data; original report serialization; weighted utility and missing ratings; agent import link/reference validation; old snapshot compatibility; independent decision-state snapshots; human/unverified brief export boundaries; and review reset when content changes.

## Local build observations

The production JS entry is approximately 405 kB before gzip (about 123 kB gzip), with locally bundled fonts and images. This is a build-size observation, not a Lighthouse or performance benchmark. No new dependency or backend was introduced for the export.
