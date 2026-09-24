# Jobfolio Frontend Architecture

This document describes the architecture, directory layout, routing conventions, state management model, and testing patterns introduced in the frontend refactor.

## Directory Structure

```
frontend/src/
├── app/
│   ├── layouts/
│   │   ├── AppLayout.tsx          # Root workspace shell (sidebar, topbar, agent run banner, breadcrumbs)
│   │   ├── JobLayout.tsx          # Job review shell (header, actions, sticky tabs)
│   │   └── SettingsLayout.tsx     # Settings shell (AI Connections & Search Sources sub-tabs)
│   ├── errors/
│   │   └── RouteErrorPage.tsx     # Route-level error boundary with refresh action
│   ├── navigation.ts              # Sidebar nav items and layout navigation metadata
│   ├── providers.tsx              # Root QueryClientProvider and app-level contexts
│   ├── query-client.ts            # Configured TanStack Query Client (no retry on 4xx)
│   └── router.tsx                 # React Router v7 routes with deep-linking & nested layouts
├── features/
│   ├── applications/
│   │   └── components/
│   │       ├── DynamicField.tsx   # Native input, textarea, select, and semantic radio fieldset
│   │       └── DynamicField.test.tsx
│   ├── documents/
│   │   └── components/
│   │       └── CVPreview.tsx      # Truthful CV paper renderer and section synthesizer
│   ├── jobs/
│   │   ├── components/
│   │   │   └── AddJobForm.tsx     # URL import and manual job description creator
│   │   └── queries.ts             # Active-only job queries, polling & cache invalidations
│   ├── review/
│   │   ├── ReviewDraftContext.tsx # Shared review draft ownership (CV check, coverage, answers)
│   │   └── ReviewDraftContext.test.tsx
│   └── workspace/
│       └── queries.ts             # Bootstrap query, settings mutations, profile save & AI structuring
├── pages/
│   ├── NotFoundPage.tsx           # 404 recovery page
│   ├── applications/
│   │   └── ApplicationsPage.tsx   # Submitted / tracking dashboard
│   ├── cv-library/
│   │   └── CvLibraryPage.tsx      # Generated CV documents & download links
│   ├── discover/
│   │   └── DiscoverPage.tsx       # Paginated (25/page) free public search opportunities
│   ├── jobs/
│   │   ├── NewJobPage.tsx         # Add job via URL or paste description
│   │   ├── JobDescriptionPage.tsx # Role details, requirements, metadata, & history
│   │   ├── JobCvPage.tsx          # Tailored CV review, wording verification & diffs
│   │   ├── JobCoveragePage.tsx    # Requirement breakdown, evidence inspection & audit
│   │   ├── JobApplicationPage.tsx # Questions, answers, package approval & submission
│   │   └── JobActivityPage.tsx    # Per-job execution & audit logs
│   ├── opportunities/
│   │   └── OpportunitiesPage.tsx  # Workspace saved jobs queue with status filters
│   ├── preferences/
│   │   └── PreferencesPage.tsx    # Job search criteria, titles, and remote settings
│   ├── profile/
│   │   └── ProfilePage.tsx        # Master profile editor with AI CV structuring
│   └── settings/
│       ├── AiConnectionsPage.tsx  # Free AI models, providers (OpenRouter/TokenRouter)
│       └── SearchSourcesPage.tsx  # Free job board sources & scraping toggles
├── shared/
│   ├── api/
│   │   ├── client.ts              # Fetch wrapper with X-Job-Agent header & AbortSignal
│   │   ├── client.test.ts         # Vitest unit tests for apiClient
│   │   └── errors.ts              # ApiError class and FastAPI 422 error extractor
│   ├── lib/
│   │   └── formatters.ts          # Score percentages, date formatting, state badges
│   ├── styles/
│   │   └── tokens.css             # Semantic CSS color tokens, fonts, and layout units
│   └── ui/
│       ├── Badge.tsx              # Status indicator badge
│       ├── Button.tsx             # Semantic button and link styled button
│       ├── Empty.tsx              # Clean empty-state container
│       ├── Field.tsx              # Form label, field wrapper, and accessible error small tag
│       └── Notice.tsx             # Alert notice (info, success, warning, error)
├── main.tsx                       # Mount point mounting <Providers><RouterProvider /></Providers>
├── style.css                      # Core layout and visual identity styles
└── types.ts                       # TypeScript schemas and data structures
```

## Routing Conventions

1. **Top-Level Routes**:
   - `/opportunities`: Queue of saved jobs with status filtering (`all`, `needs_review`, `approved`, `submitted`, `skipped`).
   - `/discover`: Discovered postings from free feeds, with 25-item pagination and search triggers.
   - `/jobs/new`: Add opportunity page via URL import or manual description paste.
   - `/cv-library`: Collection of prepared CV files ready for download.
   - `/applications`: Application tracking pipeline.
   - `/profile`: Master profile editor with AI CV structuring and offline cleanup.
   - `/preferences`: Search queries, target titles, locations, and search schedules.
   - `/settings`: Redirects to `/settings/ai`.
   - `/settings/ai`: AI model selector with free recommended models (`minimax/minimax-m3:free`, `openrouter/free`).
   - `/settings/search`: Free job search feeds configuration.

2. **Nested Job Review Routes** (`/jobs/:jobId/*`):
   - Wrap around `JobLayout` providing shared job data and `ReviewDraftProvider`.
   - `/jobs/:jobId/description`: Role requirements, source link, and metadata.
   - `/jobs/:jobId/cv`: Visual CV paper, statement diffs, and CV verification checkbox.
   - `/jobs/:jobId/coverage`: 0-100% requirement match breakdown, evidence citations, and manual overrides.
   - `/jobs/:jobId/application`: Employer form questions, package approval button, and manual/automated submission.
   - `/jobs/:jobId/activity`: Live and historical agent execution logs for the job.

3. **SPA Fallback & Deep Linking**:
   - FastAPI in `backend/app.py` serves `dist/index.html` for any GET/HEAD HTML navigation request that does not match `/api/*` or an asset file.
   - Direct loading, route refresh (`Ctrl+R`), and browser Back/Forward navigation are supported seamlessly.

## State Management & Draft Ownership

1. **Server State (TanStack Query)**:
   - Queries are cached and invalidated intentionally on mutations (e.g. `['workspace', 'bootstrap']`, `['jobs', jobId]`).
   - Polling only runs when there are active background operations (`queued` or `running` state in `bootstrap.runs`).

2. **Shared Review Draft (`ReviewDraftContext`)**:
   - Manages unsaved user edits across all sibling job tabs (`/cv`, `/coverage`, `/application`).
   - Tracks `cvChecked`, `coverageChecked`, `answers`, and requirement `supports`.
   - Synchronizes safely with server updates using `baseHash`: server refreshes do not overwrite unsaved edits if the user is dirty; saving updates the baseline cleanly.

3. **Form State**:
   - Native controls with semantic fieldsets for radio options (`aria-label`, accessible names).
   - API keys are cleared only upon successful save, not before.

## Testing Strategy

- **Unit & Component Tests**: Run with `npm.cmd test` using Vitest and React Testing Library (`DynamicField`, `ReviewDraftContext`, `apiClient`).
- **End-to-End Smoke Tests**: Run with `.\.venv\Scripts\python.exe scripts\ui_check.py` using Playwright on an isolated database without contacting real employers.
- **Backend Tests**: Run with `.\.venv\Scripts\python.exe -m pytest -q` covering all 40 integration and workflow scenarios.
