# Chanakya — run the approved frontend locally

This is the original React/TypeScript source used for the approved Chanakya Site, exported from commit `27f292aee03d789cdb36e320f4af2225004db18a` (saved Site version 3). The UI source, styles and public assets are unchanged. This export adds local setup scripts and documentation only. It does not modify or redeploy the hosted Site.

**Dark mode only. No API key or backend is required to run the existing frontend.** Live AI research is not implemented. Imported agent outputs and manual ratings work; earlier report/process screens are explicitly illustrative.

## 1. Prerequisites on Windows 11

Install Node.js **24.x**, which includes npm, and Visual Studio Code. This export was checked using Node 24.22.1 and npm 11.9.0 on Linux; running it on Windows is not independently verified. Use Node 24.x for the closest match to the checked environment. Git is optional. The application uses modern browser APIs, so use a current Chrome, Edge or Firefox.

Recommended VS Code extension: **ESLint is optional**; this project does not ship an ESLint configuration. TypeScript/JavaScript support is built into VS Code. You may add the official React Developer Tools browser extension for inspection. No extension is required to run the project.

After installing Node, close and reopen VS Code, then check in a PowerShell terminal:

```powershell
node --version
npm --version
```

If PowerShell blocks `npm.ps1`, use `npm.cmd` in place of `npm` in the commands below. You do not need to disable PowerShell protections.

## 2. Extract and open the project

Download `Chanakya-Complete-Source-Code.zip`, right-click it and choose **Extract All**. Open the extracted **chanakya** folder, the one containing `package.json`, in VS Code with **File → Open Folder**. Do not open the ZIP as a workspace.

For example, if extracted into `C:\Projects`:

```powershell
cd C:\Projects\chanakya
code .
```

In VS Code choose **Terminal → New Terminal** and select PowerShell. Check that `Get-Location` points to the folder containing `package.json`.

## 3. Install and run

```powershell
npm install
npm run dev
```

The terminal prints the exact URL. Vite normally uses `http://localhost:5173/`; if busy, it uses another available port. Open that printed URL. To start directly at the immediate reference page, open `http://localhost:5173/insights` when 5173 is the printed port.

No `.env` file is needed. `.env.example` documents that there are no current configuration variables. Do not enter AI provider credentials into browser code or variables prefixed `VITE_`.

Keep the terminal running while using the website. Press **Ctrl+C** to stop; type `npm run dev` to restart. For an explicit alternative port:

```powershell
npm run dev -- --port 5174
```

For reproducible installation from the included lockfile, you can use `npm ci` instead of `npm install`. Internet access to the npm registry is needed on first installation. All images are included in `public/assets`; font files come from the declared local `@fontsource` dependencies and are bundled at build time. The running app does not fetch its fonts or images from the original Site.

## 4. Build and checks

```powershell
npm run typecheck
npm test
npm run build
npm run preview
```

- `typecheck`: checks the application TypeScript without emitting JavaScript.
- `test`: compiles model modules into `.test-build` then runs Node's tests.
- `build`: checks TypeScript and builds the production application into `dist`.
- `preview`: serves the production build; open the URL it prints, normally `http://localhost:4173/`.

There is no lint script configured. Do not run `npm run lint` unless you add and configure one. Vite serves React Router routes directly in development and preview. When hosting `dist` elsewhere, configure an SPA fallback to `index.html`. Opening `index.html` with `file://` is not supported.

## 5. Explore the existing application

Start with `/insights`, `/`, or `/research`. Primary navigation is Overview, New Decision, My Decisions, Domains and Insights. An active decision exposes Define → Research → Deliberate → Evaluate → Consensus → Decide.

Create a question, add optional context/documents, choose a domain and review the plan. Begin Research opens the evidence workspace; it does **not** run AI. Import actual outputs using the displayed JSON format or the included `public/agent-output-schema.json`. Imported sources are unverified until checked by a human.

The council has a reading transcript alternative. Evaluation uses your 1–5 ratings and weights, with initially blank scores. Consensus groups imported positions without inventing agreement. Record your own recommendation and rationale in the final brief; save, export or copy it. Editing evidence or evaluation returns a reviewed brief to draft.

Your browser stores decisions locally. Uploaded files are in IndexedDB. A new localhost port or browser is a separate storage origin, so it will initially look empty. Existing hosted Site data is not automatically included in this ZIP or transferred to localhost. No user data, uploaded documents, credentials or browser history is packaged.

## 6. Where to edit

| Area | Files |
|---|---|
| Entry, error boundary and all routes | `src/main.tsx` |
| Sidebar, topbar and six-stage navigation | `src/experience-shell.tsx` |
| Approved landing and domain gallery | `src/experience-public.tsx` |
| CSS depth, council roles, process walkthrough | `src/experience-visuals.tsx` |
| Guided setup, research, source map, agent council | `src/decision-pages.tsx` |
| Evaluation, consensus, final brief, library, Insights | `src/decision-outcomes.tsx` |
| Original domain landings and radial overview | `src/public-pages.tsx` |
| Original setup/review/progress/settings/account views | `src/research-pages.tsx` |
| Original demo reports, source dialogs, graph | `src/result-pages.tsx` |
| Shared buttons, panels and accessible native modals | `src/components.tsx` |
| Question/filter/upload dialogs and IndexedDB files | `src/dialogs.tsx` |
| Context, persistence and toast notifications | `src/state.tsx` |
| Domain definitions, labels, examples and specifications | `src/domains.ts` |
| Draft validation, snapshots and suggestions | `src/model.ts` |
| Agent import schema validation, utility, decision export | `src/decision-model.ts` |
| Original styles then approved redesign overrides | `src/styles.css`, `src/experience.css` |
| Logos, illustrations, SVGs and dark kit images | `public/assets/` |
| HTML title and metadata | `index.html` |
| Tooling and dependencies | `package.json`, `package-lock.json`, `vite.config.ts`, `tsconfig*.json` |

There is no `services/api.ts` or backend to export: the current app has no API client. Do not add a fake service merely to make the folder structure look complete. See `docs/ARCHITECTURE.md` and `docs/INTEGRATIONS_AND_MISSING.md` for actual data flow and future server integration boundaries.

## 7. Troubleshooting

| Symptom | What to check |
|---|---|
| `npm` not recognized | Install Node.js, restart VS Code and run `node --version`. Ensure Node is on PATH. |
| PowerShell says scripts are disabled | Use `npm.cmd install` and `npm.cmd run dev`. |
| `ENOENT` / package.json missing | Use `cd` to the extracted `chanakya` folder containing `package.json`. |
| Missing package / module not found | Stop the server and run `npm ci` from the project folder. Check the installation output for registry/proxy failures. Do not copy another machine's `node_modules`. |
| Port in use | Open the new URL Vite prints, or start with `npm run dev -- --port 5174`. |
| Blank page | Use the Vite URL, not file://. Check the terminal and browser Console. Run `npm run typecheck` and `npm run build`. The error boundary offers reload and does not clear saved data. |
| Broken images | Keep the `public/assets` tree intact; root-relative `/assets/...` paths are intentional. Use the dev server at its root, not a subfolder URL. Check `docs/ASSETS.csv`. |
| TypeScript errors | Use Node 24.x, install with the included lockfile, and run `npm run typecheck`. If you edited a file, fix the first reported error and check imports and capitalization. |
| Environment variable error | None are required by the original frontend. Remove unrequested custom configuration and restart the dev server. Never expose provider secrets via Vite. |
| CORS/backend connection error | The original frontend makes no research API calls. Any such error concerns a separately added integration. Configure its server CORS for your actual local origin; do not disable browser security. |
| Saved decisions absent | localhost and the hosted Site have different storage. Keep the same browser and port. Private browsing/storage restrictions can prevent persistence; watch for the app's storage warning. |
| AI does not answer | Expected: no live agents or retrieval are connected. Use actual output import or build a server integration. Demo report screens are labelled illustrative. |
| Route works by clicking but not refresh on another host | Add an SPA fallback to index.html on that host. Vite handles this locally. |

## 8. Documentation supplied

- `docs/ROUTE_AND_COMPONENT_AUDIT.md`: actual routes, page composition, dependencies and states.
- `docs/ARCHITECTURE.md`: component, routing and state flow.
- `docs/VERIFICATION.md`: tested results and explicit verification limits.
- `docs/INTEGRATIONS_AND_MISSING.md`: complete/mocked/backend-dependent functionality and exclusions.
- `docs/ASSETS.csv`: every public asset, size, hash and visual family.
- `docs/SOURCE_PROVENANCE.json`: export origin and byte equality of original files.
- `docs/ORIGINAL_README.md`, `docs/REDESIGN_AUDIT.md`, `docs/FIGMA_HANDOFF.md`: original project documentation retained for history; current export verification is authoritative.

The `.git` history, hosted deployment binding, node_modules, builds, caches and secrets are intentionally excluded. This is a standalone local frontend export; it does not reproduce the hosting platform's ChatGPT access gate.
