# Integrations, exclusions and missing items

## Fully implemented local frontend

Navigation, eight domain contexts, question/context/specification editing and validation, guided plan, local attachment storage and text previews, validated actual-output JSON import, evidence filtering/zoom/inspection/comparison, council and transcript, editable user evaluation, position grouping and import history, human decision brief, save/restore/search/status filtering, Markdown serialization/download controls, copy sharing, follow-up decisions, local profile/preferences and responsive layouts.

## Explicit demonstration behavior

Original `/progress` uses a simulated research sequence. Original `/results` views show illustrative records and analysis structure. Their source labels do not identify genuine retrieved publications. `/signin` and `/signup` are local account form demonstrations; passwords are not stored or sent. Domain suggestions use keyword matching. None of these is silently upgraded into real AI in the export.

## Backend-dependent, not built

Live retrieval, actual multi-agent execution and debate, automated evidence verification, generated consensus/recommendations, authenticated shared accounts, cross-device persistence, cloud document storage, server-side PDF/DOCX extraction and server exports. No such backend code was available because none exists in the current source. FastAPI/PostgreSQL remain a planned direction, not a prerequisite for running the frontend.

## Missing assets

No referenced public source assets were omitted from this export. Every tracked public asset is retained at its original name and format; see ASSETS.csv. Fonts are installed with the declared @fontsource packages and bundled locally. Lucide icons are installed from the declared package; not separate image files. The font licenses are included in those installed packages. No temporary remote image URLs are required.

## Deliberate exclusions

No node_modules, dist, test output, Git history, credentials, runtime user data, documents uploaded in a browser, deployment archive or hosting identity manifest. None is required for local frontend execution. Browser-local saved data from the deployed origin does not migrate automatically. The hosting platform's ChatGPT sign-in gate is not app source and is not reproduced locally.

## Unverified aspects

The deployed Insights page is behind a sign-in wall in the inspection browser. The exact deployed source commit was verified through saved-version provenance and original application files were exported byte-for-byte. No authenticated side-by-side pixel-diff against the hosted page was possible; pixel-perfect visual equality is not claimed. Linux command checks do not constitute a Windows 11 execution test. See VERIFICATION.md for the full matrix.
