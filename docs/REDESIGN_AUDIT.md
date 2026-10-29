# Experience audit and implementation plan

Scope: existing Chanakya Site, source revision `2707678`. The live Site has an owner sign-in gate; the implementation source and local preview are the inspection baseline. This is an expert interface audit, not a claim of user research or measured task-completion improvements.

## Existing functionality and route mapping

| Existing route | Current purpose | Redesign treatment |
|---|---|---|
| `/` | Illustrated radial domain cover | Editorial product introduction, interactive council, process explainer and sample journey; original illustrated overview retained at `/illustrated-overview` |
| `/domains/:key` | Six domain landings | Keep domain content, illustrations, examples, topics and start actions; harmonize with the new design system |
| `/research` | Question, domains and recent work on one long page | Overview dashboard with one resume action and a compact recent-decisions list |
| `/confirm-domain` | Eight repeated selector cards | Preserve route and context; guided setup provides the primary domain-selection entry |
| `/setup/:key` | Quick/advanced specifications | Preserve route and fields; concise contextual header and workflow indicator |
| `/review` | Research brief | Preserve validation and editing; guided four-step plan makes the primary entry easier |
| `/progress` | Simulated five-stage progress | Preserve explicit demo status; analytical workspace added at `/decision/research` |
| `/results`, `/results/:tab`, `/followup` | Demo overview, evidence, perspectives and follow-up | Keep the complete legacy report and source dialogs; new contextual stage views link to them |
| `/graph` | Five-node evidence graph | Retain graph, node inspection and accessible mobile list; contextual evidence map in research |
| `/library` | Saved snapshots and local documents | Keep immutable snapshots, restoration, removal, attachments and sample investigation |
| `/settings` | Profile/preferences | Preserve local profile, output depth and privacy details |
| `/signin`, `/signup` | Local account demonstration | Preserve validation and explicit non-authentication boundary |
| `/research-error` | Insufficient evidence | Preserve recovery and document actions |

## Prioritized findings

1. **P0 — Unclear product entry:** the cover looks like an illustrated directory, rather than explaining collaborative decisions. Lead with the product promise, one start action, and a stage-by-stage interactive example.
2. **P0 — Missing decision stages:** deliberation, evaluation, consensus and human decision are absent from the primary navigation. Add a persistent six-stage contextual journey. Never invent agent output to fill these views.
3. **P0 — Trust boundary:** the frontend has no AI backend or verified source retrieval. Mark planned roles as awaiting output; allow actual imported outputs and manual human evaluation. No fictional confidence or consensus.
4. **P1 — Repeated panels:** reports and setup use the same rounded box composition for every paragraph. Separate editorial forms, document reading, council canvas, matrix, convergence map and executive brief.
5. **P1 — Competing navigation:** global graph/evidence links overlap report tabs. Use five primary destinations, with research tools inside the active decision.
6. **P1 — Excessive actions:** report footer and follow-up expose many equivalent buttons. Keep the main next action visible and put supporting detail in disclosure panels.
7. **P1 — Preserved context:** local snapshots work, but later decision stages need their state retained too. Extend drafts compatibly; retain old snapshots and legacy routes.
8. **P1 — Visualization semantics:** the static graph illustrates structure without actual evidence. Add a document-backed source view, honest completeness counts, editable evaluation, and agent output inspection.
9. **P2 — Motion/depth:** add CSS perspective to the council and gallery; transform/opacity-only transitions, short interaction durations, and reduced-motion fallbacks. No WebGL dependency is needed.
10. **P2 — Accessibility:** native modal behavior already works; keep focus outlines, keyboard alternatives, semantic labels and data/list alternatives to spatial views. Avoid hover-only disclosure.

## New information architecture

Primary navigation: Overview · New Decision · My Decisions · Domains · Insights. Settings remain secondary.

Active decision: Define → Research → Deliberate → Evaluate → Consensus → Decide. Four-step setup: Question → Context → Domain → Plan.

## Validation plan

Automated: existing regression tests plus weighted-score normalization, input validation, agent-import validation and compatible saved-state restoration. Browser: first-time start, context persistence, domain setup, document navigation, agent empty/import states, manual evaluation, consensus disagreement handling, save/restore, narrow-screen layout and reduced-motion CSS. Keep live AI and authentication outside the claimed implemented scope.

## Validation result

The primary journey now uses distinct stage compositions and preserves the previous routes. Twelve regression/model tests and the production TypeScript/Vite build pass. Browser checks exercised guided setup, custom subject validation, actual-output import using explicitly synthetic QA data, source inspection, map controls, excerpt comparison, council/transcript, manual matrix totals, documented disagreement, final review/save and library visibility. The narrow-screen council, menu and all six gallery illustrations rendered without document-level horizontal overflow. The gallery's implicit final row was corrected during QA.

Remaining implementation boundary: real retrieval, agent execution, authenticated cross-device persistence and independently verified sources require a backend. No simulated performance metric, confidence percentage or invented consensus was added. Legacy demo routes are retained contextually and labelled as demonstrations. Export serialization is tested; browser download delivery and formal assistive-technology/performance audits are not independently verified.
