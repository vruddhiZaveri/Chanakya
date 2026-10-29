# Chanakya Sabha

Dark-only research and decision-support workspace. The October 2026 experience redesign builds on the existing Figma-derived frontend, preserves its routes and local data, and introduces a six-stage decision journey. See `docs/REDESIGN_AUDIT.md` for the audit and route map.

## Run locally

```bash
npm install
npm run dev
```

```bash
npm test
npm run build
```

Stack: React 19, TypeScript, Vite, React Router, CSS, React Context. Fonts and illustrations are served locally. Production output is `dist/`.

## Current experience

- Editorial introduction, interactive council role previews, six-stage process walkthrough, illustrated domain discovery and guided sample plan.
- Five primary destinations: Overview, New Decision, My Decisions, Domains and Insights.
- Four-step setup: question, context/documents, domain and reviewable research plan. New questions and samples preserve the previous current brief as a local snapshot when relevant.
- Contextual journey: Define → Research → Deliberate → Evaluate → Consensus → Decide. Previous stages retain the current question and context.
- Analytical research view with source inspection, document text previews/downloads, map filtering/zoom, citation links and side-by-side original excerpt comparison.
- Spatial Sabha council and equivalent transcript. Actual imported agent statements generate position and shared-evidence relationships; missing roles are explicitly awaiting output.
- Validated JSON output import (schema in `public/agent-output-schema.json`), recorded import history and source provenance fields.
- Editable options, criteria, weights, 1–5 ratings, normalized utility bars and pros/cons/risk notes. Blank ratings stay unscored. These are user preferences, not AI confidence.
- Consensus distinguishes supporting, opposing and uncertain positions, without forcing agreement or inferring why a position changed.
- Executive decision brief with human-authored direction/rationale, review status, immutable save/restore, Markdown export, copy-to-share and follow-up decision creation.
- All original eight domain contexts, specifications, custom filters, domain landings, document storage, illustrative reports, graph, error recovery, preferences and account demonstrations remain available.

## Current boundary

The existing implementation has no research backend, verified retrieval or live agent execution. The redesign does not invent them. New stage views start with honest empty states and accept actual externally generated outputs, labelled imported and unverified. The legacy simulated progress/report screens remain explicitly identified demonstrations. Recommendations in the new brief are recorded by the human user.

No server authentication, shared accounts or cloud database is implemented. Browser-local state and IndexedDB attachments do not sync across devices. PDF/DOCX originals are retained but their text is not extracted. The Site's hosting access gate remains unchanged.

## Visual and interaction system

`src/experience.css` defines the requested charcoal, ivory, antique-gold, emerald, copper and turquoise tokens. Inter handles product UI, Cormorant Garamond the editorial headings, and system monospace structured identifiers. The six stages use distinct form, reading, council, matrix, convergence and document compositions.

Supplied illustration kit dark heroes map directly to `public/assets/kit/{sabha,grantha,nyaya,arogya,artha,nivesh,gati}-dark.png`. Original logos and domain assets remain. Dark illustrations are contained without stretching. Tiny poster assets and pale supporting images were inspected but not enlarged or placed on dark surfaces.

Council depth uses lightweight CSS perspective and SVG relationships, without a WebGL dependency. Interactive surfaces use short transform/opacity transitions; `prefers-reduced-motion` removes motion. Keyboard-visible focus, native modal focus behavior, labelled controls, council transcript and source-list alternatives remain available.

## Next backend integration

The intended backend is FastAPI with PostgreSQL. Keep the current domain specifications and question/review workflow as the request contract. Add authenticated research jobs, server-side document extraction, retrieval with verified provenance, agent orchestration, streamed progress, durable investigations and signed export/download endpoints. Replace demonstration source records only when actual source metadata and excerpts are available.

Suggested boundaries: `POST /research`, `GET /research/{id}`, `GET /research/{id}/events`, `POST /documents`, `GET /sources/{id}`, `POST /research/{id}/followups`, and authenticated library endpoints. Provider secrets belong on the server, never in Vite environment variables exposed to the client.

## Source structure

- `src/domains.ts`: domain names, questions, specifications and topic content.
- `src/model.ts`: draft validation, domain suggestions, immutable snapshots and report serialization.
- `src/state.tsx`: browser persistence, profile and workspace state.
- `src/components.tsx`: shared navigation, buttons, cards and accessible dialogs.
- `src/public-pages.tsx`: illustrated cover and domain landings.
- `src/research-pages.tsx`: setup, review, progress, library, settings and demo account forms.
- `src/result-pages.tsx`: report, evidence, perspectives and graph.
- `src/dialogs.tsx`: question/filter dialogs, attachment storage and download support.
- `src/styles.css`: retained original layouts.
- `src/decision-model.ts`: six-stage state, output validation, user utility and brief serialization.
- `src/experience-{shell,public,visuals}.tsx`: navigation, introduction, domains and spatial visuals.
- `src/decision-pages.tsx`, `src/decision-outcomes.tsx`: guided setup and all six contextual stages.
- `src/experience.css`: redesign tokens, compositions, depth, motion and responsive rules.
- `tests/domain.test.mjs`: state and data integrity tests.

## Validation

Twelve automated tests cover original domain data and persistence plus weighted-score normalization, missing ratings, import validation, old snapshot compatibility, deep-cloned decision state and exported limitations. TypeScript and production build pass.

Redesign browser QA covered fresh-question validation, context/custom domain/plan setup, research entry, synthetic JSON import, citation inspection, filtering/zoom/no-match state, two-source excerpt comparison, council/transcript, opposing positions retained through consensus, manual evaluation totals, human review/save and the decision library. Synthetic QA records exist only in the preview browser, never in the shipped source. A 390px iframe check confirmed council/menu/domain rendering with no document-level horizontal overflow. Reduced-motion behavior was checked in source; no automated screen-reader or performance benchmark is claimed.

Previous regression QA covered local text attachments, original report/save/restore routes and a 390px domain setup view. Browser automation did not observe the blob-download event, so end-to-end file delivery remains unverified despite working export serialization and download controls.

## Design reference

[Figma final prototype page](https://www.figma.com/design/iGsAiK26SJ4DagODV4RcDK/CHANAKYA?node-id=2056-11)

The Figma file was read during implementation, not modified. Older learning and reader reference flows were excluded from the active implementation.
