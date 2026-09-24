# Jobfolio

A personal job-search and CV-review app for Walid Hamdy. React/TypeScript dashboard, Python/FastAPI service, SQLite storage, and Playwright application adapters. The provided PDF is imported locally on first launch and remains unchanged.

## Start on Windows

Requires Python 3.11+ and Node.js 20.19+ or 22.12+.

```powershell
powershell -ExecutionPolicy Bypass -File .\start.ps1
```

Open http://127.0.0.1:8765 in a browser. The server binds only to loopback. First launch installs dependencies and Chromium if needed. Stop it with `powershell -ExecutionPolicy Bypass -File .\stop.ps1`.

Before the first launch, place your own master CV PDF in the project root. Personal PDFs and the local `data/` directory are excluded from Git. Without a master CV, the app cannot build a profile or tailor applications. The checked-in tests that assert Walid Hamdy's imported profile require his private source PDF locally.

## First use

1. Review **My profile**. The original two-page PDF is available from Original CV. Confirm any corrections or added evidence before saving.
2. Save **Search preferences**, including titles and location. Defaults suggest frontend titles from the CV; geography and authorization are intentionally unconfirmed.
3. In **Connections**, the app defaults to **100% Free Operation**:
   - **Job Search**: Uses public feeds from Remotive, Jobicy, and Arbeitnow out of the box with zero API keys and zero cost. Brave Search is optional if you have a subscription key.
   - **AI Tailoring**: Select **OpenRouter** (default) with free models such as `meta-llama/llama-3.3-70b-instruct:free`, `google/gemini-2.0-flash-exp:free`, or `openrouter/free`. OpenRouter accounts and keys are free with a $0 balance. **OpenCode** (free Zen models), local endpoints (Ollama/LMStudio), or paid **OpenAI** are also supported. Keys are stored securely in Windows Credential Manager.
4. Use **Find jobs**, **Import a link**, or **Paste a description**. Finding jobs uses free feeds and applies your saved title, location, and posting-date criteria. Imports can initially contain only a feed summary; preparing a CV retries the full posting and asks for a pasted description when it cannot retrieve one. Greenhouse and Lever have dedicated posting adapters.
5. Prepare a local CV, or use AI tailoring. Local mode preserves original statements and reorders skill groups completely offline without any API calls. AI mode extracts requirements, edits eligible prose, performs a second factual check, and assesses the finished CV. Employer/title/date/education/skill entries remain exact.
6. Review the whole CV and every requirement. Adjust support ratings only where evidence exists. If evidence is missing, add truthful details to the master profile and prepare again. Coverage is `100 × sum(weight × support) / sum(weight)`, with required weight 3, preferred weight 1, and full/partial/missing support 1/.5/0. This is not an ATS score or a prediction of hiring success.
7. On **Application**, inspect supported employer forms, complete answers, save review, and approve the exact package. Use **Draft a cover letter** when needed; the draft has PDF/Word downloads and becomes part of the approval. Recognized cover-letter text fields and uploads use the reviewed draft. **Submit application** is a separate explicit action. LinkedIn Co-Pilot can assist after approval, but unattended Auto-Apply is disabled while screening answers need review. Other sites, CAPTCHA, login, custom controls, or unsupported uploads require manual completion.
8. Track confirmations under **Applications**. If a submission is uncertain, check the employer confirmation before explicitly resolving it. No automatic retry occurs after a submit click.

## Local data and external services

- `data/agent.sqlite3`: profile, preferences, jobs, package versions, approvals, worker runs, and history.
- `data/documents/<package-id>/`: generated DOCX and PDF versions, with SHA-256 checksums.
- `data/receipts/`: employer confirmation screenshots when available.
- `data/server*.log`: local server diagnostics; HTTP access logging is disabled.
- Original source PDF remains at the project root. `.gitignore` excludes all personal documents, data, credentials, and test artifacts.
- Job search runs 100% free by querying public job feeds (Remotive, Jobicy, Arbeitnow). No CV data is sent during search.
- When AI tailoring is enabled, only CV evidence statements and job requirements are sent to the configured provider (OpenRouter, OpenCode, or OpenAI); contact details (email, phone, address) are strictly excluded from AI prompts. Provider calls use `store=False`.
- CV generation uses python-docx. If `SOFFICE_PATH` points to a LibreOffice executable, PDF is converted from DOCX. Otherwise ReportLab generates a portable PDF from the identical structured content; pagination and type layout can differ between Word and PDF. No office suite is required for the fallback.

## Implementation boundaries

One persistent queue worker runs one operation at a time. Pending work is marked interrupted after restart, and in-flight submissions become uncertain. Approvals are invalidated by package edits or master-profile changes. Document hash checks run again before download, approval and submission. Submission is claimed transactionally to prevent double clicks. Required answers, form fingerprints and a unique submit button are checked before sending. A detected confirmation is required for automatic submitted status; manually recorded results are labelled as such.

The browser uses isolated temporary contexts and never your existing browser profile. Hosted forms change; unsupported forms fail closed with a manual handoff. No employer application was submitted during development. AI semantic assessments and factual audits remain fallible and need your review. The app does not automatically search on a schedule, message recruiters, infer visa eligibility, or claim interview outcomes. Salary and location uncertainties are highlighted for review rather than guessed.

## Development and validation

```powershell
.\.venv\Scripts\python.exe -m pytest -q
cd frontend
npm.cmd run build
```

Run the backend with `python -m uvicorn backend.app:app --host 127.0.0.1 --port 8765 --no-access-log`. The production frontend is served by FastAPI from `frontend/dist`. After frontend changes run the build again; restart the server when backend code changes.

Tests use temporary databases and local browser fixtures. They cover master import, duplicate jobs, scoring, DOCX/PDF text parity, stale approvals, altered files, CSRF/host restrictions, profile revisions, API setup failures, required fields, changed forms, post-click uncertainty, and duplicate submission prevention. They do not submit to live employers or make paid AI calls.

The machine-readable API schema is at `/openapi.json`. Profile/preference/settings updates use PUT; discovery and worker actions use POST. Mutating requests require `X-Job-Agent: local` and same-origin requests. Multi-provider AI (OpenRouter, OpenCode, OpenAI, Custom) and Search feeds (Remotive, Jobicy, Arbeitnow, Brave) are isolated in `backend/providers.py` and `backend/search.py`; application platform handling is in `backend/browser.py` and `backend/network.py`.

Current validation environment: generated PDFs were visually inspected; DOCX content parity was checked, but Word-specific visual rendering was unavailable because the bundled runtime has no LibreOffice. AI and Brave calls need your credentials and have not been exercised with a paid account. Greenhouse and Lever posting imports were checked read-only against public endpoints. Hosted-form submission was tested only against controlled local fixtures.
