# Architecture

## Entry and composition

React 19 is mounted by `src/main.tsx` with StrictMode, a React class error boundary, React Router BrowserRouter, and WorkspaceProvider. Public landing/domain routes have their own composition. Workspace routes render inside WorkspaceShell through an Outlet. There is no server-rendering layer and no authentication dependency for local execution.

WorkspaceShell owns only the responsive navigation toggle. It selects the active stage from the path, records the last stage, closes mobile navigation on page changes and scrolls to the top. The current question and analytical data belong to the provider, not the route component, so switching stages preserves them.

## State and persistence

WorkspaceProvider owns `draft`, immutable saved `library` snapshots, profile and notifications. It initializes browser data with core draft validation and persists JSON under `chanakya-workspace-v1`. Storage failures display a session-only warning. Files are stored separately in IndexedDB database `chanakya-documents`, object store `files`; the draft holds metadata and optional text previews. Native file selection, text parsing, download and clipboard use browser APIs.

A Draft contains question, domain, six domain specifications, depth, attached document metadata, selected cross-domain lenses and recorded follow-ups. Its optional DecisionState adds objectives, constraints, success criteria, last stage, imported proposition/agents/sources/history, weighted criteria/options, user recommendation/rationale and human-review status. Old snapshots acquire default decision fields through getDecision. saveSnapshot uses structuredClone so later edits cannot change the saved copy.

## Data flow

1. A question is validated and keyword rules suggest a domain; no model runs for domain classification.
2. Guided setup updates context and specifications in the shared draft.
3. Research displays attached documents and validated imported source records.
4. parseAgentBundle validates role IDs, positions, source references and HTTP(S) URLs before updating state. Source authenticity is not independently verified.
5. Council connections come from actual shared source IDs or opposing imported positions. The reading transcript represents the same imported data.
6. Evaluation computes normalized utility from explicit user weights and ratings. Missing/invalid ratings stay unscored; no fabricated source-credibility or confidence values exist.
7. Consensus groups support/oppose/uncertain positions and recorded imports. A single snapshot cannot establish causal changes in reasoning.
8. The user writes a direction and rationale, marks a brief reviewed, and saves/exports/copies it. Content edits reset review status; navigation alone does not.

## Styling, graphics and assets

CSS is loaded in order: styles.css followed by experience.css. The latter contains approved dark tokens and stage compositions. Avoid reversing the imports. Local @fontsource Inter weights 400/500/600/700 and Cormorant Garamond 700/500 italic reproduce typography. Monospace uses system fonts. Lucide React supplies code-defined icons; public SVGs supply original custom icons and plaques. No Recharts or WebGL is used: the existing council uses CSS perspective and evidence connections use SVG. Motion is removed under prefers-reduced-motion.

Responsive breakpoints in source include 1200, 1000 and 767 CSS pixels. Secondary panels stack and the sidebar becomes a mobile drawer; native dialogs become bottom sheets. Native buttons and labelled fields retain keyboard operation and focus styling. Complex spatial views have transcript/source list alternatives.

## Backend contract boundary

No API client, backend, secrets or database connection exists in this revision. The JSON import schema is the only concrete external-output interface. A future backend can supply validated proposition, agents and sources to the existing DecisionState; see `public/agent-output-schema.json`. Proposed job/upload/authentication APIs in the historical README are plans, not implemented contracts. Keep secrets on a server, and preserve the approved UI when adding integration.
