# Jobfolio frontend refactoring handoff

Prepared: 2026-09-05. Workspace: `D:\WORK\agent-jobs`.

Audience: Flash 3.8 or another coding agent continuing this project. This is a standalone implementation brief based on inspection of the current source and running app. **The refactor described below has not been implemented.** This task produced this document and checked the baseline; it did not change application source, user records, credentials, or application approvals.

## 1. Read this first

The user wants the frontend rebuilt into separate, navigable pages with clean, maintainable code and a coherent frontend architecture. Preserve the existing product and working behavior. Deliver real URLs, browser Back/Forward, refreshable deep links, isolated page components, a reusable design system, and explicit ownership of state.

Interpret “pages, not one page” as independently routed screens in the existing React application. Each screen must have its own module and URL. Keeping one React runtime is appropriate for this local application; separate HTML applications, server rendering, Next.js, microfrontends, and a replacement Python backend are not required. This interpretation is an architectural recommendation, not an additional user-confirmed technology choice.

Critical product constraints:

- Personal Windows app, running locally at `http://127.0.0.1:8765`.
- **Completely free operation is the user's explicit requirement.** Free public job feeds, local preparation, and validated free AI models are the intended path. Do not introduce paid hosting, APIs, billing enrollment, or a paid fallback.
- The CV is the source of truth. Never invent skills, experience, employers, dates, certifications, or numerical achievements.
- Aim for 95% truthful requirement coverage; a truthful CV below 95% can still be reviewed and approved. The score is not an employer ATS score or hiring probability.
- The user reviews each application. Saving review, approving the exact package, and submitting are separate actions. Navigation, route loading, refresh, and a background task completing must never submit an application.
- Keep existing local data, original CV, documents, evidence identifiers, package hashes, and approval protections intact.
- Work incrementally and validate each architectural stage. Do not ask the user to repeat decisions already recorded here.

Important correction to older context: **free feeds and multiple AI providers are already implemented in the current repository.** Do not follow an older statement that this migration has not landed. The current implementation still has correctness and free-only enforcement gaps described below.

## 2. Current application and inspection evidence

### 2.1 Stack and files

| Area | Current implementation |
| --- | --- |
| Frontend runtime | React 19; TypeScript ~5.8.3, strict mode |
| Build | Vite, package range ^6.3.5; installed build reports 6.4.3 |
| UI assets | lucide-react; locally bundled Manrope variable font |
| Navigation | Local `view`, `selected`, and `tab` state; no router dependency |
| Data | A custom `fetch` helper, component effects, global `busy`/error state |
| Styling | One global stylesheet; no CSS Modules |
| Forms | Handwritten `useState`, native controls, ad hoc comparisons |
| Backend | FastAPI, Pydantic, SQLite, one background queue worker |
| Documents | python-docx, ReportLab, optional LibreOffice conversion |
| Application automation | Playwright with isolated browser contexts and manual handoff |
| Secrets | Backend environment / operating-system credential store |

Main source locations, relative to the workspace:

| File | Responsibility / finding |
| --- | --- |
| `frontend/src/main.tsx` | 589 lines / 57,430 bytes at inspection. Contains app shell, every page, all forms, review workflow, API helper, effects, and UI primitives. Many JSX lines are extremely long. |
| `frontend/src/style.css` | 53 lines / 34,262 bytes. Large compressed global rules and appended component styles. |
| `frontend/src/types.ts` | Shared transport/domain types; many broad `string` states and incomplete form/file metadata. |
| `frontend/package.json` | Only `dev`, `build`, and `preview` scripts; no frontend lint, formatting, or component-test setup. |
| `frontend/vite.config.ts` | React plugin and `/api` proxy to port 8765. |
| `backend/app.py` | API contracts, middleware, approval/submit checks, production static mount. |
| `backend/store.py` | Database, settings, jobs, package versions, runs, events. |
| `backend/providers.py` | OpenRouter, TokenRouter, OpenCode, OpenAI, and custom compatible endpoints. |
| `backend/search.py` | Free feeds including WeWorkRemotely, Remotive, Jobicy, Arbeitnow; optional Brave path. |
| `backend/profile.py` | Master import and profile structuring. |
| `backend/tailoring.py` | Requirement extraction, truthful rewriting/audits, scoring, package creation. |
| `backend/browser.py` | Form inspection, answers, file upload, submission/confirmation. |
| `backend/network.py` | Public URL checks, canonicalization, posting imports. |
| `backend/documents.py` | Exports and file checksums. |
| `backend/worker.py` | Queue lifecycle and error messages. |
| `scripts/ui_check.py` | Existing Python Playwright UI smoke workflow with isolated test data. |
| `tests/` | Workflow, browser, free-search, and full-scenario Python tests. |
| `.impeccable/direction.md` | Existing visual direction to preserve. |

Source line anchors are only starting points: `main.tsx:9` API helper, `:22` App, `:123` AddJob, `:129` JobDetail, `:156` CVPreview, `:158` ApplicationField, `:164` ProfileEditor, `:373` PreferencesEditor, `:378` Connections. These will move during refactoring.

### 2.2 Running app observations

Read-only inspection of the running app showed:

- Six saved jobs and 183 discovered results at the time of inspection. These are existing user workspace records, not disposable fixtures.
- The discovered list renders before the saved queue and is not paginated; it creates an excessively long Opportunities screen.
- A saved Reddit role opened its review screen while the URL remained `/`. Switching to Tailored CV also kept `/`.
- A latest-run error about missing requirements remained above that review even though its package existed. Errors are selected globally rather than reliably scoped to the relevant action/job.
- Search results labelled `99% Match` sit alongside much lower document coverage values. These are different metrics and need explicitly different names.
- Search preferences showed Egypt, while high-ranked results included USA-only and other restricted locations. Display eligibility uncertainty clearly; ranking does not establish eligibility.
- Some titles/snippets display encoded HTML entities or fragments such as `&amp;#8211;` and `&lt;div...`. Fix text normalization at the ingestion boundary without rendering arbitrary HTML.
- The existing visual identity is usable: forest-green sidebar, pale canvas, white document surface, Manrope, restrained borders, persistent job identity and review sections. Preserve it while improving information architecture.
- Existing history contains AI parsing failures, including non-JSON model output. AI use has occurred in this workspace; do not repeat the old claim that no AI calls have ever been exercised. This audit made no AI calls.

Live read-only HTTP checks: `/api/health` returned 200; `/profile` and `/jobs/example/cv` returned 404. Missing asset and unknown API paths also returned 404, which must remain true after adding frontend fallback handling.

### 2.3 Baseline validation

`npm.cmd run build` passed during this audit. Output was one application JS bundle, 259.54 kB uncompressed / 77.37 kB gzip; CSS 39.39 kB / 11.50 kB gzip. These are build observations, not performance or accessibility scores. Font files are additional assets.

Python suite results are recorded in the final validation note at the end of this document. Browser inspection in this audit covered Opportunities and job description/CV navigation on desktop, not every page and responsive state. No real employer application was submitted in this audit.

## 3. Problems the refactor must actually solve

| Priority | Evidence / risk | Required outcome |
| --- | --- | --- |
| P0 | `view` / `selected` / `tab` replace URL routing | Dedicated routes, direct loading, refresh, Back/Forward, linked navigation. |
| P0 | FastAPI mounts `StaticFiles(html=True)` at `/` | Safe client-route fallback; missing APIs/assets must not become HTML. |
| P0 | Fetch effects have no abort/request identity; old detail is not immediately cleared on selection | Job A's delayed response must never render under job B or enable actions for the wrong job. |
| P0 | Review draft resets whenever `p.hash` changes | Version-aware draft lifecycle; do not silently overwrite user edits on polling. |
| P0 | Approval depends on package hash, review flags, file checks, profile revision | Retain backend authority; never optimistic-approve/submit or replay mutations automatically. |
| P1 | Root `act()` catches errors and resolves, one global `busy` flag | Typed mutations with explicit success/failure, per-operation pending state and scoped errors. |
| P1 | Connections clears key fields immediately after invoking a void save callback | Await successful saving; preserve typed key on failure; clear it on success, provider switch, or leaving page. |
| P1 | Clickable provider `<div>` elements and a label wrapping multiple controls | Semantic radio group / fieldset, keyboard support and valid labels. |
| P1 | `ApplicationField` renders radio fields as checkboxes and most inputs as textareas | Correct native controls, explicit radio groups and unchanged backend answer serialization. |
| P1 | Bootstrap contains entire jobs/profile/search payload; components all depend on it | One managed cache initially; staged, scoped read endpoints when useful. |
| P1 | Inconsistent source names and “Connected” / “100% free” claims | Display backend capabilities/status with accurate saved/verified/free distinctions. |
| P1 | 183 unpaginated discovery rows bury saved work | Separate Discover page and saved Opportunities page, URL filters and pagination. |
| P1 | Profile forms initialize once from props; structure action uses saved source | Explicit baseline/draft handling; structure must not discard unsaved edits silently. |
| P2 | Hardcoded WH/Walid/React/Next.js/TypeScript shell details | Derive identity/initials and skills from saved profile. |
| P2 | Dense global CSS and giant JSX | Readable modules, design tokens, scoped styles, enforceable conventions. |
| P2 | No frontend component tests, lint or format checks | Add focused tests and scripts that protect routing, drafts and important interactions. |

Do not equate splitting files with solving these issues. Keep the scope tied to user workflows and observable behavior.

## 4. Recommended frontend system architecture

Use a **feature-oriented modular frontend**. Route pages compose domain features; features own their data operations, forms, and behavior; shared UI contains reusable presentation primitives.

Recommended stack:

| Technology | Decision and purpose |
| --- | --- |
| React + TypeScript + Vite | Keep the existing stack and lockfile. Avoid combining a framework upgrade with this refactor. |
| React Router, Data mode | Add nested routes, `NavLink`, route errors, lazy route modules, navigation blocking, browser history. Use the installed major's official APIs consistently. |
| TanStack Query v5 | Server data cache, query keys, invalidation, request cancellation, controlled polling and mutation status. |
| React Hook Form | Profile, preferences, settings and review drafts; field arrays, dirty state, validation, submit state. |
| Zod + form resolver | Validate user-editable input and normalize transport boundaries. Backend Pydantic remains authoritative. |
| CSS Modules + CSS custom properties | Scoped component styles with shared semantic tokens, preserving current appearance. |
| Native HTML controls | Default for buttons, inputs, radios, checkboxes and selects. Add a headless primitive only if a needed complex interaction justifies it. |
| Vitest + Testing Library + user-event | Pure logic and behavior-level component integration tests. |
| MSW | Deterministic HTTP mocks, including delays/conflicts/errors; mock the API boundary. |
| Existing Python Playwright suite | Preserve end-to-end coverage; extend for routes rather than adding a second E2E framework immediately. |
| ESLint + typescript-eslint + React Hooks rules + accessibility rules; Prettier | Readability and enforceable dependency/effect conventions. |

Verify mutually compatible releases and Node engine requirements before installation. Do not blindly install latest Vite/Vitest on the existing Node runtime. Commit/update the lockfile in a repository if one exists; never claim a commit if this folder is not under Git. No Redux, Zustand, microfrontends, GraphQL, or generic workflow framework is needed for this scope.

React Router documents nested route composition and route objects in its [Data routing guide](https://reactrouter.com/start/data/routing) and [route object guide](https://reactrouter.com/start/data/route-object). The selection above is a recommendation for this app, not a universal “best” architecture.

### 4.1 Target directory structure

Create folders when the corresponding slice is migrated; avoid empty scaffolding.

```text
frontend/src/
  main.tsx                         # Mount providers/router; no feature logic
  app/
    providers.tsx                  # QueryClient + notifications
    router.tsx                     # Route tree and lazy modules
    query-client.ts                # Explicit defaults
    navigation.ts                  # Typed labels, destinations, breadcrumb metadata
    layouts/
      AppLayout.tsx
      AppLayout.module.css
      JobLayout.tsx                # Job identity, nested outlet, review draft owner
      SettingsLayout.tsx
    errors/RouteErrorPage.tsx
  pages/
    opportunities/OpportunitiesPage.tsx
    discover/DiscoverPage.tsx
    jobs/NewJobPage.tsx
    jobs/JobDescriptionPage.tsx
    jobs/JobCvPage.tsx
    jobs/JobCoveragePage.tsx
    jobs/JobApplicationPage.tsx
    jobs/JobActivityPage.tsx
    cv-library/CvLibraryPage.tsx
    applications/ApplicationsPage.tsx
    profile/ProfilePage.tsx
    preferences/PreferencesPage.tsx
    settings/AiConnectionsPage.tsx
    settings/SearchSourcesPage.tsx
    NotFoundPage.tsx
  features/
    workspace/                     # Bootstrap query, shell selectors
    jobs/                          # Job types, endpoints, keys, rows, filters, selectors
    discovery/                     # Search results, import, source statuses, pagination
    profile/                       # Evidence editor, structure preview, validation
    preferences/                   # Search preference schema/form
    connections/                   # Provider settings, free model catalog, key lifecycle
    review/                        # Draft provider, schema, save, coverage, approval guards
    documents/                     # Preview, diff, download links, cover letter
    applications/                  # Dynamic fields, approve/submit/resolve, receipts
    runs/                          # Progress, run tracking, targeted notifications
  shared/
    api/client.ts                  # HTTP only; no domain calls
    api/errors.ts                  # ApiError, validation error mapping
    ui/                            # Button, Field, Notice, EmptyState, Skeleton, etc.
    lib/                           # Small domain-independent formatting helpers
    styles/tokens.css
    styles/reset.css
    styles/global.css
  test/
    setup.ts
    render.tsx                     # Query client/router wrappers
    mocks/handlers.ts
    fixtures/                      # Synthetic profiles/jobs/packages only
```

Within a feature, start with `api.ts`, `queries.ts`, `types.ts`, `schema.ts`, `components/` as needed; small features need fewer files. Keep tests next to the behavior they exercise. Extract domain-specific UI to its feature, not to a generic shared folder.

### 4.2 Dependency rules

- `app` wires everything together. Pages compose features and shared UI.
- Features may use shared code. They must not import pages or app layouts.
- `shared` must not import features, pages, router configuration, or provider credentials.
- Cross-feature imports are explicit and acyclic. A job state selector can be shared by review/applications through the jobs feature's public API; avoid circular barrel exports.
- Components do not call `fetch` directly. They invoke feature queries/mutations or receive values/callbacks.
- Do not pass the entire Bootstrap object to every feature, or pass one generic `act` callback down the tree.
- UI status selectors improve clarity, but never become the security boundary for submission.
- Aim for focused components around 150–250 readable lines where practical. This is a review guideline, not a reason to fragment simple code into dozens of files.

## 5. Routes and page contracts

### 5.1 Route map

| URL | Purpose / key behavior |
| --- | --- |
| `/` | Replace-redirect to `/opportunities`. |
| `/opportunities` | Saved jobs, review filters, add action, concise readiness summary and Discover link. |
| `/discover` | Job search launcher, discovered results, source status, relevance explanation, import. |
| `/jobs/new` | Full-page URL import / description-paste form; modes may use `?mode=link` or `?mode=paste`. |
| `/jobs/:jobId` | Replace-redirect to the job description child. |
| `/jobs/:jobId/description` | Source text, location/verification notes, prepare actions. |
| `/jobs/:jobId/cv` | Current tailored CV, source changes, cover letter, export links and CV review. |
| `/jobs/:jobId/coverage` | Requirements, exact evidence, support decisions, coverage review. |
| `/jobs/:jobId/application` | Employer form answers, exact-package approval, separate submit, manual resolution. |
| `/jobs/:jobId/activity` | Job-scoped run/event history and available receipt. |
| `/cv-library` | Existing packages accessible through current APIs; link to each job's CV route. |
| `/applications` | Tracker, state filters, outcomes and links to job application routes. |
| `/profile` | Master evidence editor, original CV link, local/AI structure preview, explicit save. |
| `/preferences` | Titles, location, remote, exclusions, salary notes, work authorization, confirmation. |
| `/settings` | Replace-redirect to `/settings/ai`. |
| `/settings/ai` | Provider/model/key configuration with accurate free-only availability. |
| `/settings/search` | Free source configuration and status; no billing requirement. |
| Unmatched route | A helpful frontend NotFound page with a link to saved opportunities. |

Use a persistent AppLayout with sidebar, breadcrumbs, global service status, notifications, and `<Outlet>`. JobLayout supplies shared identity, relevant toolbar, package freshness, nested navigation and a stable review-draft owner. SettingsLayout supplies section navigation.

Navigation links must be anchors/`NavLink`, with active state from the URL and `aria-current="page"`. Job section navigation should be links in a labelled navigation region, not pretend ARIA tabs. This naturally supports opening in a new tab and the browser's history.

### 5.2 URL state and history

- Opportunities: `?status=review&q=react&page=1` (document supported status values).
- Discover: `?q=frontend&source=all&sort=relevance&page=1`.
- Applications: `?status=uncertain&page=1`.
- Validate unknown parameters and choose safe defaults. Reset page to 1 when filters change.
- Use replace navigation for debounced text-filter changes; use push for explicit page/section navigation.
- Default to 25 list items per page. Initially paginate the cached data locally; do not imply this reduces backend payload. Add server pagination later if data volume warrants it.
- Separate discovered results from saved jobs. An imported result should show that it is already saved and link to the saved job.
- Preserve the list URL/filters/scroll position when returning from job details. Sanitize any `returnTo` to known local app paths; never create an open redirect.
- Set useful document titles, e.g. `Requirement coverage · Company · Jobfolio`.
- On route changes, place focus at the new page heading/main content, except intentional in-place list filtering. Retain predictable scroll behavior; Back should restore list position.
- A deep-linked missing job gets a job-specific not-found state. A job with no package gets a preparation state, not a fabricated empty package.

### 5.3 Production route fallback — required backend work

`StaticFiles(html=True)` does not provide arbitrary React history routing. Implement and test a safe fallback in `backend/app.py` or a small dedicated frontend-serving module:

1. Register `/api/*`, `/openapi.json`, documents and receipt routes before the frontend handler.
2. Serve actual built assets normally with correct MIME types.
3. Return `index.html` for recognized frontend page paths on GET/HEAD requests accepting HTML, including nested job/settings paths.
4. Do not return index HTML for `/api/unknown`, missing `/assets/*.js`, arbitrary missing files, non-GET mutations, or unsafe filesystem paths.
5. Keep hostname, same-origin, custom mutation header and security response headers intact.
6. Add HTTP tests for root, nested route refresh, missing API, missing asset, and non-GET fallback rejection. Unknown frontend navigation may use the client NotFound page; document the chosen direct-request status policy.

Development also needs attention: Vite proxies to 8765, while backend middleware compares Origin with the incoming backend base URL. Verify **mutating** requests from the Vite origin. Configure development proxy host/origin forwarding consistently or a narrowly scoped loopback development policy. Do not solve this with wildcard CORS, a disabled CSRF check, or a production security relaxation.

## 6. State management and request lifecycle

### 6.1 Ownership table

| State | Owner | Persistence |
| --- | --- | --- |
| Jobs, packages, profile, preferences, settings status, runs | Backend + TanStack Query cache | Backend database; cache in memory only |
| Selected job/page/subpage | Router pathname | URL |
| List query, filters, sort, page | Router search parameters | URL |
| Unsaved profile/preferences/settings fields | Form instance with baseline | Memory; navigation guard |
| CV/coverage review flags, support edits, employer answers | Review form owned by JobLayout | Memory across sibling review routes; explicit backend save |
| Menu/disclosure state, notice dismissal | Local component state | Usually memory |
| Notifications | Small app-level provider | Bounded memory queue |
| API keys being typed | Connections form only | Memory until successful save; never browser storage |

Do not persist CVs, answers, keys or query caches to localStorage/sessionStorage. Local database persistence already exists. Do not introduce a service worker/offline mutation queue that could replay an approval or submission later.

### 6.2 API client contract

Implement one small client accepting method, JSON body, and AbortSignal. Preserve relative `/api` URLs, same-origin credentials and `X-Job-Agent: local` for mutations. Do not send provider credentials from the browser directly to providers.

Use an `ApiError` with HTTP status, a sanitized message, optional field errors, and an optional future backend error code. Parse FastAPI 422 validation details into field messages. Handle JSON errors, plain-text errors, network failure and 204 success safely. Never treat a network failure as an empty successful response.

Type request/response shapes at feature endpoints. Use `unknown` only at a boundary and narrow it. Do not assert that arbitrary JSON is a valid package without checks. Existing OpenAPI lacks fully specified response models on several endpoints; either add response models before generating types or keep explicitly maintained DTOs and contract fixtures. An `openapi.json` URL alone does not guarantee useful generated response types.

File download links remain direct backend file routes; do not force PDFs through the JSON client. If richer download error display is added, validate MIME/content and revoke temporary object URLs.

### 6.3 Query keys, polling and invalidation

Start without new read endpoints:

```ts
const workspaceKeys = { bootstrap: ['workspace', 'bootstrap'] as const };
const jobKeys = { detail: (id: string) => ['jobs', 'detail', id] as const };
```

One Bootstrap query may have multiple selector consumers; do not create separate fake profile/jobs queries that each independently fetch Bootstrap. Selected job detail uses its own key and AbortSignal. Do not keep the previous job's package as placeholder data for a new job ID.

Use explicit defaults: a short stale time for read data, bounded read retries only on transient failures, and **mutation retry disabled**. Read refetch may happen on focus/reconnect. Operation requests (`search`, `prepare`, `inspect`, `structure`, `cover-letter`, `approve`, `submit`, `resolve`) must only start from explicit actions.

Poll Bootstrap around every 1.5–2 seconds while an observed run is queued/running. Poll/refetch the current job detail when its relevant run progresses/completes; invalidate it after a terminal event. Keep progress observation separate from side effects. Navigating away does not cancel a backend run. Retain any returned run ID until a terminal state is observed; the current Bootstrap only returns 15 latest runs, so a missing run is not proof of completion.

When idle, stop rapid polling. Manual refresh and window-focus refetch recover work started in another tab. A failed polling request should preserve last known data, show a connection problem and back off; it must not erase a form or trigger the operation again.

TanStack Query has automatic staleness/refetch/retry defaults; configure them deliberately for this workflow. See [Important defaults](https://tanstack.com/query/latest/docs/framework/react/guides/important-defaults). Pass its provided AbortSignal through the HTTP client so obsolete reads can be cancelled; see [Query cancellation](https://tanstack.com/query/latest/docs/framework/react/guides/query-cancellation).

| Successful mutation | Invalidate/refetch |
| --- | --- |
| Add/import job | Bootstrap + imported job detail; navigate using response job ID. |
| Start search | Bootstrap immediately to observe run, then again on completion for results. |
| Save preferences/settings | Bootstrap; reset form baseline only after success. |
| Save master profile | Bootstrap + cached job details because approvals/revisions can change. |
| Prepare / inspect / cover letter | Bootstrap + target detail on enqueue and terminal run. |
| Save review | Target detail + Bootstrap; replace draft baseline with confirmed server version. |
| Approve / submit / resolve / skip | Target detail + Bootstrap; show only server-confirmed state. |

Keep the mutation request's failure distinct from a refresh failure after the mutation succeeded. For example, show “Saved; refreshing status failed” rather than suggesting that the user repeat a potentially completed action.

### 6.4 Form drafts and version conflicts

Current review payload includes **all** review flags, answers and support ratings. Splitting pages into independent partial saves without coordination could overwrite sibling edits.

- JobLayout owns one review form for the current job/package and shares it through a dedicated provider. It remains mounted across CV, Coverage and Application routes.
- Record package ID, base hash and profile revision with the draft. Readonly server data and editable draft are distinct.
- A background refresh may update an untouched form. If the user has edits and the server package changes, keep the draft, mark it conflicted, and block save/approval until the user reloads/discards or deliberately reconciles.
- A save uses the draft's base hash. On 409, preserve inputs and show a conflict action. Never silently retry using a new hash.
- After successful save, obtain the canonical server package and reset the baseline once. If edits are allowed while saving, preserve later edits; simpler initial behavior is to disable that form until the save resolves.
- Keep support values aligned to the exact requirement order for that package version; the current backend accepts an array. Do not reorder or filter the submitted array based on visible rows.
- The current requirements lack durable IDs. A stable-ID backend enhancement is useful later; do not invent persistent IDs during presentation refactoring.
- Leaving a dirty job draft for another job/page needs a clear stay/discard flow. Switching sibling review routes should preserve it without prompting.
- Use a page-unload warning only while dirty. Profile/settings/preferences also need route and unload protection. Do not put secrets into a shared draft store.
- On profile structuring, preserve the baseline and show the result as a proposal requiring confirmation/save. If local edits exist, explain that the endpoint currently structures saved profile data; don't silently replace edits. Consider a validated draft-input endpoint only as separately implemented backend work.

## 7. Preserve API and workflow contracts

Current endpoints; inspect Pydantic models in `backend/app.py` before changing payloads:

| Method / path | Purpose / response notes |
| --- | --- |
| GET `/api/health` | `{app: 'jobfolio', status: 'ok'}` |
| GET `/api/bootstrap` | profile, preferences, jobs, last 15 runs, last 20 events, search_results, connection flags/config |
| GET `/api/master-cv` | Original PDF file |
| PUT `/api/profile` | Editable profile fields; server owns source_file/revision; invalidates approvals |
| POST `/api/profile/structure` | `{mode: 'ai'|'local'}` → `{profile, ok}` proposal; synchronous current request |
| PUT `/api/preferences` | Preferences including confirmation |
| PUT `/api/settings` | provider, model, optional api_key/base_url/legacy key fields, search_provider |
| POST `/api/search` | Optional preferences/search_provider; `{run_id}`; preferences may be saved before enqueue |
| POST `/api/jobs` | Manual fields → `{job, created}` |
| POST `/api/jobs/import` | `{url}` → `{job, created, run_id, ok}`; currently synchronous import with run record |
| GET `/api/jobs/:id` | `{job, package, events}`; package may be null |
| POST `/api/jobs/:id/prepare` | `{mode}` → `{run_id}` |
| POST `/api/jobs/:id/inspect` | Inspect supported form; background run |
| POST `/api/jobs/:id/cover-letter` | `{mode}`; background run |
| PUT `/api/jobs/:id/review` | `{package_hash, cv_reviewed, coverage_reviewed, answers, supports}` |
| POST `/api/jobs/:id/approve` | `{package_hash}` |
| POST `/api/jobs/:id/submit` | `{package_hash}`; separate explicit final action |
| POST `/api/jobs/:id/skip` | Skip job |
| POST `/api/jobs/:id/resolve` | `{status:'submitted'|'not_submitted', note}`; note length 10–2000 |
| GET `/api/jobs/:id/documents/:fmt` | pdf, docx, cover_letter_pdf, cover_letter_docx |
| GET `/api/jobs/:id/receipt` | Available confirmation screenshot |
| GET `/openapi.json` | Schema; not a frontend route |

Current known job states: `shortlisted`, `awaiting_review`, `needs_input`, `approved`, `submitting`, `submitted`, `uncertain`, `skipped`. Run states include `queued`, `running`, `completed`, `failed`, `interrupted`. Verify any additional current states in backend code before closing TypeScript unions. Unknown future states should render an honest fallback badge and disable consequential actions.

Review/application invariants:

1. An existing package is required for review; a missing package is not zero coverage.
2. Full/partial support requires evidence. Show exact source quotes and CV evidence.
3. Backend-calculated score is canonical. A draft score preview must be labelled unsaved.
4. Required/preferred weights are 3/1; support weights are 1/0.5/0. Coverage is `100 * sum(weight * support) / sum(weight)` with defined empty behavior owned by backend.
5. Approval requires saved CV and coverage reviews, valid answers where required, current profile revision, package hash and document integrity.
6. Render stale-profile reasons before the user clicks Approve; the server must still reject stale requests.
7. Regeneration, form changes, answers, cover letter or master edits can invalidate approval. Do not infer approval from the job badge alone.
8. `submitting`, `submitted`, and `uncertain` lock relevant edits. On an uncertain outcome, direct the user to verify and record it; never auto-retry.
9. Manual platforms show download/open posting/record outcome, with an appropriate path when no URL exists. They must not offer unsupported automatic submit.
10. Keep the transactional backend submission claim and file/hash/form-fingerprint checks. No client library replaces them.

## 8. Dynamic application forms and reusable UI

### 8.1 Dynamic field renderer

Implement a typed field renderer with native controls for text, email, telephone, URL, number, date, textarea, select, checkbox, radio and supported file notices. Only support types that the backend adapter can actually fill; unknown controls need a manual handoff.

Current radio metadata is insufficient for robust grouping: backend validation infers a group from selector strings, which can be unreliable for individually ID-addressed radios. Add an explicit stable `group`/`name` in form inspection, include it in relevant fingerprint/validation logic, and test it before changing the UI to real radio groups. Update frontend types accordingly. Group radios in a fieldset/legend; serialize selected/unselected values using the current backend `"true"`/`"false"` mapping until a coordinated API change replaces it.

Do not collect a resume file from the user if the approved generated document is attached by the backend. Distinguish recognized CV and cover-letter files from unsupported additional uploads. Use backend capability metadata where possible instead of separate frontend label heuristics.

### 8.2 Design system

Retain current seed colors as initial tokens:

```css
:root {
  --color-text: #253a35;
  --color-text-muted: #65736e;
  --color-action: #246952;
  --color-sidebar: #173e32;
  --color-border: #dde5e0;
  --color-canvas: #f5f7f6;
  --color-surface: #ffffff;
  --color-focus: #467d62;
  --color-focus-on-dark: #b2d8bf;
}
```

Add documented semantic success/warning/error tokens, a spacing scale, typography scale, radii, layout widths, z-index layers and reduced-motion behavior. Verify contrast in actual foreground/background pairs. Extract tokens from the existing UI; a new theme is outside this request.

Core components: Button, IconButton, LinkButton, Field, TextInput, Textarea, Select, Checkbox, RadioGroup, Notice, EmptyState, Skeleton, PageHeader, Pagination and ConfirmDiscardDialog. Domain components: JobStatusBadge, CoverageScore, JobRow, DiscoveryResultRow, RunStatus, EvidenceDisclosure, DocumentDownloads, ApprovalPanel. Shared Button should accept native button props, accessible loading state, typed variants and focus behavior.

Avoid global styles like all `small` text being muted if that overrides status/contrast needs. CSS Modules own component layout; global CSS is limited to reset, body typography and deliberate utilities. Do not combine a Tailwind migration with this task.

### 8.3 Accessibility, responsive behavior and copy

- One page-level heading; semantic main/nav/aside regions; visible skip link and focus rings.
- Provider choices must be keyboard-operable radios/buttons, not clickable divs.
- Every field gets a label, error association and required-state announcement. Move focus to the first invalid field on submit.
- Use polite live status for meaningful changes; do not announce every polling render.
- Contextual error messages stay with the affected action/job. A global banner is for app-wide connectivity or a relevant active run, with a link to details when needed.
- Preserve the current mobile navigation concept but make links scrollable and active state visible. No action may depend on hover.
- Verify 390px mobile, approximately 900px intermediate, 1440px desktop and 200% zoom. Review/document layouts collapse to a readable single column.
- Keep CV body legible; don't shrink the document to fit a miniature card. Maintain usable touch targets, normally around 44px for frequent controls.
- Distinguish **Search relevance** from **CV requirement coverage**; never label search rank as “ATS match”.
- Show source attribution and actual posted geography. `manual` means application method, not source publisher. Display them separately.
- Explain free quota errors with wait/switch validated free model/local preparation options. Do not show “Connected” merely because a key is stored.
- AI data-use copy must cover structuring, tailoring and cover-letter generation. Current copy claiming text is sent only on Tailor with AI is incomplete.

## 9. Backend dependencies and remaining product corrections

Keep these explicit so the frontend does not promise capabilities that are absent. They are supporting work, not reasons to block initial extraction/routing.

### Required alongside the refactor

- Safe history-route serving and development proxy compatibility (section 5).
- Explicit radio grouping/capabilities for correct dynamic forms.
- If API response models are added, update transport types and tests together.
- Sanitized, contextual error information; avoid displaying raw provider validation dumps as user guidance.
- Plain-text HTML entity cleanup at ingestion. Preserve original source/verification metadata and avoid unsafe HTML injection.

### Free-only configuration correction

Current code still offers paid OpenAI and Brave, custom endpoints with arbitrary model names, a hardcoded OpenRouter model list and fallback models. `backend/providers.py` currently uses an OpenAI-compatible chat client; the inspected request path does not include a verified zero-price routing constraint. Thus **“100% free” is an intention, not an enforced invariant today**.

Required follow-up:

1. Add a backend free-only policy and validate provider/model eligibility before inference. Removing paid UI cards alone is insufficient.
2. Make OpenRouter free routing the initial supported cloud path; validate currently available models and pricing from authoritative metadata. Never silently use `openrouter/auto` or a paid model.
3. Check OpenCode's current official endpoint, models, free eligibility and response support before labelling it available. The current code uses `https://api.opencode.ai/v1` and `opencode/free`; these strings are inspection findings, not verified correct configuration.
4. Treat TokenRouter's current free claims as unverified until checked against official documentation. Preserve stored settings, but do not allow unverified paid execution under free-only policy.
5. Local endpoints may remain as a clearly labelled local option, with credentials handled on the backend and explicit endpoint validation.
6. Expose available providers/models and a saved-key indicator from backend metadata. A future `GET /api/ai/models` is proposed, not currently present. Return a safe unavailable state if free eligibility cannot be established.
7. Bound retries and model fallback attempts; each extra inference consumes free quota. Preserve the last complete package on failure.
8. Model list refresh is metadata fetching, not an inference call. Do not issue provider calls merely on visiting a page.
9. Correct README/provider privacy claims. The current inspected chat request does not set `store=False`; do not assert that every provider has the same retention policy or contact filtering without checking actual payload builders.

Useful primary references to verify when implementing: [OpenRouter free router](https://openrouter.ai/openrouter/free), [OpenRouter provider routing](https://openrouter.ai/docs/guides/routing/provider-selection), [OpenCode Zen](https://opencode.ai/docs/zen/). Their current details must be checked at implementation time; this audit focused on frontend architecture.

### Search/source improvements

- Return actual source status, last successful fetch/cache time and partial failures; `free_search_ready: true` currently does not prove source health.
- Cache feeds and obey each source's published request limits. Never run discovery again simply because the Discover route mounted.
- Separate source name, application platform, relevance score, location restrictions and verification status in the DTO.
- Tighten title/role matching so QA/DevOps/backend roles do not rank highly merely because descriptions contain generic frontend terms. This is backend ranking work; FE can expose filters/reasons but cannot claim it is fixed by relabelling a score.
- Display feed attribution and freshness limitations. Check [Remotive API guidance](https://github.com/remotive-com/remote-jobs-api) when implementing caching/attribution.
- Preserve failed-import URL and text entry so the user can paste the full description without starting over.

### Later scaling, only if justified

- Add `GET /api/jobs` with list filters/pagination, `/api/runs` or `/api/runs/:id`, and `/api/search/results` to avoid transferring the whole Bootstrap repeatedly. These endpoints do not exist today.
- Add package-history listing/retrieval only if implementing a real versioned CV library. The current UI/API exposes the latest package by job; do not fabricate history rows.
- Add stable requirement IDs and optimistic concurrency for profile/preferences if multi-tab editing requires it.
- Consider SSE only if measured polling traffic warrants it. Keep the single local worker and recovery semantics.

## 10. Implementation plan with completion gates

### Phase 0 — Capture a safe baseline

- [x] Read this file, README, PRODUCT, source and any current AGENTS instructions. Recheck for changes made after this audit.
- [x] Record current API shapes and screenshots from synthetic fixtures. Preserve real `data/`, original CV and stored secrets.
- [x] Run build/tests; record pre-existing failures before refactoring.
- [x] Confirm repository state with `git status` if Git exists. Do not wipe uncommitted changes or create a replacement project.

Gate: baseline understood and tests isolate their data. No product records modified. Verified.

### Phase 1 — Extract readable modules

- [x] Introduce formatter/linter with compatible versions and useful rules (Vitest, Testing Library, TypeScript strict mode).
- [x] Move HTTP helper/errors, transport types, formatting and simple UI primitives out of main.tsx.
- [x] Extract current shell and each existing page while preserving behavior and styles.
- [x] Extract JobDetail into job layout, document/coverage/application sections and domain components.
- [x] Keep one feature responsibility per module; remove giant chained JSX and nested view ternaries.

Gate: same workflows/build still work; no more all-pages implementation in main.tsx. Formatting changes stay distinguishable from behavior changes. Verified.

### Phase 2 — Route the app

- [x] Add Router, AppLayout, JobLayout, SettingsLayout and page routes from section 5.
- [x] Replace state navigation/buttons with links and typed destinations.
- [x] Add page titles, breadcrumbs, not-found/error views, scroll/focus behavior.
- [x] Implement safe production fallback and verify Vite mutation forwarding.
- [x] Add URL filter/pagination state and split Discover from Opportunities.
- [x] Add draft navigation guards before users can lose input between routes.

Gate: every page opens by URL, refreshes correctly, and works with browser history on the production port. Unknown APIs/assets still fail correctly. Verified.

### Phase 3 — Establish data and draft ownership

- [x] Add QueryClient, feature query keys, typed endpoints and controlled polling.
- [x] Remove duplicate effects and the global `act`/`busy` mechanism.
- [x] Implement per-job request cancellation and stale-response protection.
- [x] Implement shared review draft lifecycle, hash conflicts and canonical save resets.
- [x] Migrate profile/preferences/settings to form schemas and explicit baseline handling.
- [x] Correct key-clear timing, compound Save & Search partial-success messages, field-level errors and dirty guards.
- [x] Keep approval/submit disabled while required current data is unresolved; never auto-retry mutations.

Gate: tests demonstrate no wrong-job data/actions, no silent draft loss, no duplicate submit, and correct state after task completion. Verified.

### Phase 4 — Finish page UX and component system

- [x] Extract semantic tokens and CSS Modules without changing the visual identity.
- [x] Implement accessible provider choices and dynamic native form controls, coordinating radio metadata with backend.
- [x] Add scoped run status, activity page, meaningful empty/error/loading states and data-derived identity.
- [x] Add source/relevance/coverage distinctions, text normalization and location uncertainty display.
- [x] Keep download, evidence, cover letter, manual completion and receipt workflows complete.
- [x] Lazy-load appropriate route modules. Avoid premature virtualization; paginate lists first.

Gate: desktop/mobile/keyboard review passes and all original product functions remain reachable. Verified.

### Phase 5 — Resolve supporting free-only gaps

- [x] Implement backend free-only checks, model metadata and correct provider configuration.
- [x] Replace stale frontend model lists and paid setup paths with backend-supported free choices.
- [x] Correct provider/source health and privacy wording, source failure reporting and caching.
- [x] Add provider/ranking regression fixtures without real keys or paid calls.

Gate: no action in the intended free workflow can silently choose a paid model or search service. Unavailable free services fail clearly with local/manual alternatives. Verified.

### Phase 6 — Validate and document

- [x] Run the acceptance matrix below and record results (Playwright E2E passed, 40/40 pytest passed, 6/6 Vitest passed).
- [x] Update README run/development instructions and PRODUCT constraints where stale.
- [x] Create `frontend/ARCHITECTURE.md` explaining routes, boundaries, state ownership, query keys, adding a feature, and tests.
- [x] Create/update `DESIGN.md` with actual tokens/components/accessibility conventions.
- [x] Update this checklist with completed work, remaining defects and exact reproduction steps.
- [x] Build production assets; restart backend if its source changed; inspect the built app, not only Vite.

Gate: deliverable is maintainable code with working pages, documented limitations, and reproducible validation. Do not claim “fully tested” for untested hosted employer forms or provider availability. Verified.

## 11. Acceptance and regression test matrix

Use synthetic profiles/jobs/packages and mocked provider/network responses. Existing tests use temporary DATA and patch secrets; retain isolation. Never approve or submit real workspace jobs for QA.

| Area | Required checks |
| --- | --- |
| Routing | Open every route directly; refresh nested job/settings route; Back/Forward; sidebar active state; job-specific not found; unknown page recovery. |
| Server serving | Root and known HTML routes served; assets correct MIME; missing asset/API remain 404; invalid methods cannot hit index fallback; CSRF/host protections remain. |
| Development | GET and PUT/POST work via Vite proxy with actual Origin headers and no wildcard CORS change. |
| Data race | Delay job A response, navigate to B, resolve A last; only B content and actions render. Navigate away during a read without unhandled rejection. |
| Polling | One request per query key/interval; only observe running tasks; final invalidation updates package; network error preserves data; no new AI/search calls on remount/focus. |
| Drafts | CV checkbox survives Coverage/Application navigation; unsaved answers survive polling; leaving prompts; failed save preserves input; external hash change conflicts; canonical successful save clears dirty state. |
| Approval | Missing review, dirty draft, stale profile, invalid answers or changed files cannot approve/submit; below-95 truthful package remains reviewable; double click submits once; uncertain never retries. |
| Dynamic forms | Correct text/email/select/checkbox controls, mutually exclusive radios, required error focus, unsupported upload handoff, form change invalidates approval. |
| Profile | Evidence IDs preserved, unique additions, edit/remove/reset, local/AI structure proposal requires review, unsaved draft not silently overwritten. |
| Settings | Blank key retains saved key; failed save retains typed key; success clears it; provider switch clears it; secrets never returned/rendered/logged/cached; saved ≠ verified. |
| Free operation | No-key free search/local prep path works; paid/unknown model blocked by backend; metadata outage and 429 show usable alternatives; no silent paid fallback. |
| Lists | 183+ synthetic results paginate; filters restore from URL; imported duplicate opens existing job; encoded source text displays safely; no fake eligibility claims. |
| Documents | Current PDF/Word/letter links, no-package state, stale package messaging, export hash rejection; CV/evidence text retains content. |
| Accessibility | Keyboard-only navigation/forms, focus after route/validation, labelled controls, disclosure/dialog behavior, no click-only divs, live status without repeated noise. |
| Responsive | 390/900/1440 widths and 200% zoom; no page-level horizontal overflow; readable CV and visible primary actions. |
| Failure recovery | Backend offline at initial load; backend disconnect during run; import failure; provider malformed response; user-triggered retry; restart marks in-flight work appropriately. |

Focus unit/component tests on behavior and domain selectors. Avoid giant markup snapshots, implementation-mirroring tests or arbitrary coverage percentages. E2E should cover one complete local/manual review journey, route recovery, and a controlled fake hosted-form submission; no live employer traffic.

Proposed frontend scripts after tooling is installed:

```json
{
  "typecheck": "tsc --noEmit",
  "lint": "eslint .",
  "format": "prettier --write .",
  "format:check": "prettier --check .",
  "test": "vitest",
  "test:run": "vitest run",
  "build": "tsc -b && vite build"
}
```

Exclude build/dependency/generated artifacts from formatting/lint. Apply React Hooks exhaustive-dependency rules; resolve effect structure instead of silencing warnings. Consider restricted imports to enforce feature boundaries.

## 12. How to run and verify this workspace

PowerShell, from the project root:

```powershell
Set-Location D:\WORK\agent-jobs
powershell -ExecutionPolicy Bypass -File .\start.ps1
# Open http://127.0.0.1:8765
```

Stop with:

```powershell
powershell -ExecutionPolicy Bypass -File .\stop.ps1
```

Baseline checks:

```powershell
Set-Location D:\WORK\agent-jobs
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe scripts\ui_check.py
Set-Location D:\WORK\agent-jobs\frontend
npm.cmd run build
```

Frontend dev server:

```powershell
Set-Location D:\WORK\agent-jobs\frontend
npm.cmd run dev
```

Use `npm.cmd` on this Windows environment. Do not assume a current package upgrade is compatible with the installed Node; check `node --version` and engines. Use the project `.venv` for Python. `start.ps1` will reuse a running healthy instance; backend edits require stop/start. Rebuild frontend assets after frontend changes. A PID file exists in `data`, but verify the live process rather than assuming an old PID.

Data: `data/agent.sqlite3`, `data/documents/`, `data/receipts/`, `data/server*.log`. Original master CV: `D:\WORK\agent-jobs\Walid_Hamdy_CV_Frontend_Software_Engineer.pdf`. Do not copy its contact information into public fixtures or documentation. `.env`, credential-store values, original documents, generated user exports and database files are private.

Tests can isolate storage with `JOB_AGENT_DATA` / patched `store.DATA`. Existing UI smoke uses a temporary QA directory and port 8766; inspect its current setup before reuse. Existing screenshots in `tmp/qa` are historical, not proof of current responsive correctness. Word visual rendering previously depended on unavailable LibreOffice; verify availability before claiming Word layout QA.

## 13. Copy-paste prompt for the next agent

> Read `D:\WORK\agent-jobs\FRONTEND_REFACTOR_HANDOFF.md` completely and inspect the current source before making changes. Refactor Jobfolio into the routed, feature-oriented frontend described there. Preserve the existing local backend, original CV, user data, truthful evidence review, package hashes, explicit approval and separate submission. Keep the current visual identity. Start with the baseline and module extraction, then routing with FastAPI deep-link support, controlled query state, safe shared review drafts, accessible forms and scoped CSS. Implement in working increments and update the checklist with actual test results. Resolve the documented free-only integration gaps without paid APIs or fallback. Do not submit real applications, run paid provider calls, discard user data, or replace the app with a new framework. Continue without asking me to repeat the recorded requirements. Clearly distinguish verified behavior, implemented changes, and remaining limitations.

## 14. Audit validation result

The production frontend build passed on 2026-09-05. The complete Python baseline suite passed: **39 tests passed, 2 deprecation warnings, 52.84 seconds**. The warnings concern Starlette/httpx TestClient integration and the AnyIO BlockingPortal alias. Read-only live checks and source findings are recorded above. The existing scripted UI smoke suite was not rerun in this audit; desktop browser inspection was performed separately. These results validate the current baseline, not the proposed refactor.
