# Route inventory and component audit

Source: approved deployed commit `27f292aee03d789cdb36e320f4af2225004db18a`. Inventory is grounded in the original source, not inferred from a generic feature checklist. The hosted `/insights` page requires sign-in in the inspection browser; authenticated live page-by-page pixel comparison was unavailable. No content was invented to fill that access gap.

## Shared specifications (apply to each workspace route below)

- Exact layout/spacing/dimensions, auto-sized panels, border radii and effects remain in the unmodified CSS files. Source preservation is more authoritative than a retyped approximate spacing table.
- Palette: base `#14191D`, elevated `#1C2429`, secondary surface `#242E33`, text `#F2EEE5`, secondary text `#A9B5B4`, borders `#344047`, gold `#C6A66B`, saffron `#C7824F`, emerald `#398579`, copper `#A86E55`, turquoise `#78B7AE`. Domain illustrations retain their original grading/accent treatment.
- Typography: Inter 400/500/600/700 product UI; Cormorant Garamond 700 editorial headings and 500 italic; system monospace for labels and identifiers. Exact font sizes/line heights/letter spacing are unchanged in source CSS.
- WorkspaceShell supplies sidebar, topbar, five primary destinations, local connection status, profile/settings and contextual six-stage progress. Public routes own their headers. Every route uses the exact existing CSS selectors and Lucide/SVG assets.
- Shared states: global error boundary, browser-storage failure warning, transient toast and native modal focus/escape behavior. All content is browser-local; there is no backend loading state to reconstruct. Native file reads and demonstration progress have their own states.
- Responsive rules, focus treatment, hover feedback, CSS perspective and prefers-reduced-motion fallbacks remain unchanged.

## Actual route matrix

| Route | Component | Composition | Interactions / navigation | Data dependencies | Responsive and state behavior |
|---|---|---|---|---|---|
| / | ExperienceLanding | Editorial split hero and CSS council; process tabs; asymmetric domain gallery; sample plan and footer. | Role preview modal; stage tabs; sample creates draft and archives existing context; domain links. | Static roles/domains plus provider draft; no remote dependency. | Public header collapses; hero/gallery stack; no loading needed. |
| /insights | Insights | Editorial three-part evidence/disagreement/precision guidance and current workspace counts; no KPI dashboard, charts or invented confidence. | Links to Research, Consensus and Evaluation. | DecisionState source/role/option counts. | Single-column editorial sections at narrow widths; legitimate zero counts. |
| /research | Dashboard | Greeting, large continue-decision panel, six-step track, attention column, recent list and principle quote. | Resume last stage; new draft; restore saved question; view all. | Current draft, saved library, optional profile. | Two-column main becomes stacked; empty recent list offers start action. |
| /new-decision | NewDecision | Focused editorial question form; left setup outline; context form; illustrated domain grid; reviewable plan. | Four steps via ?step=0..3; ?new=1 starts blank and archives meaningful previous draft; validation; advanced specs; upload modal. | Draft/context and domain definitions; documents in IndexedDB. | Outline becomes compact step row; inputs/grid stack; inline validation messages. |
| /domains | DomainsPage | Asymmetric six-domain illustrated gallery and custom-subject invitation. | Domain landing links; new decision. | Six named domain definitions and /assets/kit images. | Gallery has explicit narrow-screen rows; images contained; no backend/loading. |
| /domains/:key | DomainLanding | Domain header, editorial hero/artwork, source-practice example, topic grid, three-step explanation and footer. | Start research or example; topic question; privacy/accessibility/help modal; sign-in link. | Keys grantha, nyaya, arogya, artha, nivesh, gati; static text/images and provider draft. | Hero/topic grid stack; demo labels visible. Unknown key falls back to Grantha. |
| /illustrated-overview | Overview | Original large radial Chanakya illustration with six independently selectable hotspots/plaques and process strip. | Six domain links; custom/cross-domain actions; research entry. | Original overview art, plaque SVGs and static domain placement data. | Proportional illustration and hotspots; no new alternate UI invented. |
| /decision/research | DecisionResearch | Three-panel outline/reading/inspector; Summary, Evidence Map and Sources views. | Tab switching; source filter; map title filter and zoom/reset; node inspection; source comparison; document upload/download; output JSON import. | Actual imported sources/agents, attached metadata/text. ?source=id selects a citation. | Panels stack; map scrolls; source list alternative. Honest no-evidence/no-match states; upload/import errors and toast. |
| /decision/council | AgentCouncil | Radial Sabha scene with central question, five role seats and right reasoning inspector; transcript alternative. | Select role; council/transcript tabs; import real outputs; source citation links. | Imported role statements/positions/source IDs; CSS/SVG relationships derive from supplied data. | Canvas shrinks and inspector stacks; transcript always available; absent roles say Awaiting output. |
| /decision/evaluate | Evaluation | Full-width editable weighted matrix, horizontal utility comparison and assessment disclosures. | Rename/add/remove options or criteria; edit weights/ratings; expand methodology and pros/cons/risks. | Explicit user-entered criteria/weights/ratings. No AI scores. | Matrix scrolls horizontally rather than dropping columns; incomplete ratings stay unscored. |
| /decision/consensus | Consensus | Imported proposition; role-position paths into Agreed/Contested/Unresolved lanes; history and explanatory text. | Expand actual statements/import history; revisit council; prepare final brief. | Actual support/oppose/uncertain records and snapshots, not inferred causal history. | Lanes and role list stack; no forced convergence; missing outputs remain explicit. |
| /decision/final | FinalDecision | Executive brief masthead, question, human direction/rationale, evidence, trade-offs, uncertainty and next steps. | Review toggle; save; Markdown export; copy-to-share dialog; reopen; compare; follow-up modal. | Draft, user evaluation/recommendation, imported source records and library snapshots. | Document becomes single column; actions wrap; empty rationale/direction validation; save/copy notifications. |
| /library | MyDecisions | Compact searchable/status-filtered saved decision list; document disclosure and sample-plan action. | Restore immutable snapshot; remove confirmation; search/status filter; upload documents. | Browser-local library; current documents; no cloud sync. | List and controls wrap; empty and no-match messages; deletion has explicit confirmation. |
| /research/explore | ResearchHome | Retained original question entry, suggestions, domain selection and recent work. | Edit question; suggestion buttons; continue/domain confirmation; restore prior work. | Static domains, keyword suggestions, draft and local library. | Original responsive layouts retained; question validation and empty library state. |
| /confirm-domain | ConfirmDomain | Retained domain confirmation selectors and editable question context. | Choose one of eight contexts and continue to setup. | Keyword-based suggestions and domain definitions. | Selectors stack; selection is visual and textual. |
| /setup/:key | Setup | Retained question/context, quick/advanced specification grid, output depth and documents. | ?mode=advanced exposes all six fields; field dialogs/custom values; edit question; change domain; review. | Eight contexts: grantha,nyaya,arogya,artha,nivesh,gati,custom,multi. | Grid stacks; custom subject and multi-domain validation; invalid key redirects to research. |
| /review | Review | Retained question/specifications/depth/documents and explicit demo-process explanation. | Edit question, add documents, back to setup, start demonstration. | Current valid draft; no server job. | Readable stacked summary; validation before process. |
| /progress | Progress | Retained timed five-stage demonstration of retrieval/review/synthesis; labelled simulated. | Progress lifecycle; complete into report; cancellation/recovery controls as source. | Local timer and draft only. | Timeline stacks; reduced motion; does not imply live AI. |
| /results | Results | Original illustrative report overview, analysis sections, uncertainty, source record and follow-up area. | Save, export confirmation, edit follow-up, refine specifications and source/uncertainty/comparison dialogs. | Static domain summaries and current question; illustrative source records. | Cards stack; demo status is explicit; original source record is not a publication. |
| /results/:tab | Results | Same report shell with actual tabs overview, evidence and perspectives; graph navigation routes to /graph. | Tab navigation; evidence source dialogs; document preview; source comparison. | Static illustrative analysis plus actual attached documents. | Responsive report shell; unrecognized tab has no fabricated view. |
| /followup | Results | Original report shell with recorded follow-up questions and refinement controls. | Edit follow-up, focus India, refine context, save/export. | Draft follow-up history; no generated response. | Recorded local questions shown as such; not a live conversation. |
| /graph | Graph | Original five-node illustrative knowledge graph and node detail panel. | Select graph node and inspect; return to report. | Static diagram with current domain/question context. | Mobile accessible list; graph is illustrative, not a retrieved network. |
| /settings | Settings | Local profile, preferences and privacy/storage information. | Edit/save profile and output depth/preferences; notification. | Local provider profile/draft only. | Form stacks; no server settings or real account. |
| /signin | Account | Local demonstration sign-in form with email/password. | Form validation and local profile setup; navigate to signup or research. | No authentication API. Password not sent or stored. | Single-column form; required email/eight-character validation; explicit demo notice. |
| /signup | Account signup | Same local account composition with full-name field. | Required-name/email/password validation and local profile entry. | No server account or shared login. | Responsive form; demonstration notice retained. |
| /research-error | ResearchError | Retained insufficient-evidence recovery explanation and current question. | Revise specs, upload, retry demo or return to overview. | Current draft; simulated retry only. | Clear stacked recovery actions; no fabricated successful retrieval. |
| * | Not-found view | Existing workspace-shell fallback with one clear return action. | Open research workspace. | No server dependency. | Same responsive shell; no broken generic links introduced. |

## Component inventory

The following exports are present in the original source. Private helper components remain in the same files as their callers. No directory reorganization was performed because it could break an exact export for no user benefit.

| Source file | Exported components and helpers |
|---|---|
| `src/components.tsx` | `Button`, `ButtonLink`, `Card`, `Heading`, `QuestionCard`, `DepthPicker`, `Modal`, `Footer`, `DomainContext` |
| `src/decision-outcomes.tsx` | `Evaluation`, `Consensus`, `FinalDecision`, `MyDecisions`, `Insights` |
| `src/decision-pages.tsx` | `useDecision`, `StageHeading`, `StageNext`, `Dashboard`, `SavedDecisionRow`, `NewDecision`, `ImportOutputs`, `DecisionResearch`, `AgentCouncil` |
| `src/dialogs.tsx` | `EditQuestion`, `FieldDialog`, `downloadBlob`, `UploadDialog`, `Documents`, `ComparisonDialog` |
| `src/experience-public.tsx` | `DomainGallery`, `ExperienceLanding`, `DomainsPage` |
| `src/experience-shell.tsx` | `stageForPath`, `WorkspaceShell` |
| `src/experience-visuals.tsx` | `CouncilScene`, `ProcessExplorer` |
| `src/public-pages.tsx` | `Overview`, `DomainLanding` |
| `src/research-pages.tsx` | `DomainCards`, `ResearchHome`, `ConfirmDomain`, `Setup`, `Review`, `Progress`, `Library`, `Settings`, `Account`, `ResearchError` |
| `src/result-pages.tsx` | `SourceRecord`, `SourceDialog`, `Results`, `Graph` |
| `src/state.tsx` | `WorkspaceProvider`, `useWorkspace` |

## Asset, interaction and data audit

The exact public asset inventory is in ASSETS.csv, including hashes. Logos, domain plaques, topic SVGs, isolated domain illustrations, original council/radial art and seven dark kit images are retained. Fonts are dependency assets, while Lucide icons are compiled code; neither needs a fabricated public/icons folder.

The current source contains real stateful navigation, filtering, inputs, modals, disclosures, copy/export controls and snapshots. It contains no hidden research API, LLM provider key or server. The current Insights page has three editorial sections (evidence is not certainty; a challenge is useful; transparency over precision), links to relevant stages and actual workspace counts. It has no KPI charts, financial analytics filters, confidence dashboard or automated consensus metric.

## Inspection limits

All listed source routes/components were inventoried. Browser validation details are recorded separately; source inspection alone does not mean every possible state or interaction was browser-tested. Unknown parameter values use the existing source behavior rather than a newly invented fallback screen.
