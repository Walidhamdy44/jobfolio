# Jobfolio Global Job Search & Universal Import Test Report
**Date:** September 5, 2026
**Status:** All Test Cases Passed (100% Verified)
**Scope:** Direct LinkedIn Search, Google Jobs (Serper API), Brave Web Search, Public Feeds, and Universal Job Importer.

---

## 1. Architecture Overview

Jobfolio now features a multi-tiered global discovery and import engine:

```
                                  ┌───────────────────────────┐
                                  │   User Search Preferences │
                                  │  (Titles, Location, Rem)  │
                                  └─────────────┬─────────────┘
                                                │
                 ┌──────────────────────────────┼──────────────────────────────┐
                 ▼                              ▼                              ▼
    ┌───────────────────────────┐  ┌───────────────────────────┐  ┌───────────────────────────┐
    │     100% FREE DEFAULT     │  │   GOOGLE JOBS (SERPER)    │  │     BRAVE SEARCH API      │
    │  • Direct LinkedIn Search │  │  • Aggregates LinkedIn,   │  │  • Global web search      │
    │  • WeWorkRemotely (WWR)   │  │    Indeed, Glassdoor,     │  │  • Direct employer sites  │
    │  • Jobicy                 │  │    ZipRecruiter, Portals  │  │  • Requires Brave token   │
    │  • Remotive               │  │  • Requires Serper key    │  └───────────────────────────┘
    │  • Arbeitnow              │  │    (2,500 free queries)   │
    │  (Zero API Keys Needed)   │  └───────────────────────────┘
    └───────────────────────────┘
                 │
                 ▼
    ┌──────────────────────────────────────────────────────────┐
    │                 UNIVERSAL JOB IMPORTER                   │
    │  • Direct LinkedIn URL Parser (full descriptions)        │
    │  • Greenhouse & Lever API Adapters                       │
    │  • WeWorkRemotely RSS Feed Matcher                       │
    │  • JSON-LD Schema.org JobPosting Extractor               │
    │  • Open Web HTML Semantic Extractor                      │
    │  • In-Place Full Description Editor & Paster             │
    └──────────────────────────────────────────────────────────┘
```

---

## 2. Test Cases & Execution Matrix

| Test ID | Area | Scenario / Description | Input / Preconditions | Expected Result | Actual Result | Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **TC-01** | LinkedIn Direct | Query LinkedIn Guest API with local regional filters (e.g. Cairo, Egypt) | `keywords='Frontend Engineer'`, `location='Egypt'`, `remote_only=False` | Returns real LinkedIn postings with company, title, location, and canonical URL. | Returned 10+ jobs including *Frontend Software Engineer at Axis (Cairo, Egypt)*, *Front End Engineer at Octane*, *Senior Frontend Engineer at Zeal*. | **PASS** |
| **TC-02** | LinkedIn Direct | Query LinkedIn Guest API with Worldwide / Remote filter | `keywords='Senior React Developer'`, `remote_only=True` | LinkedIn query appends `f_WT=2` (remote) and fetches remote postings. | Correctly formatted remote query and returned remote roles. | **PASS** |
| **TC-03** | LinkedIn Import | Paste/Import direct LinkedIn Job URL (`linkedin.com/jobs/view/...`) | URL: `https://eg.linkedin.com/jobs/view/frontend-software-engineer-at-axis-4451761914` | Parses numeric job ID, calls LinkedIn guest posting API, extracts title, company, location, and full description. | Extracted *Frontend Software Engineer* at *Axis* in *Cairo, Egypt* with 3,460 chars of complete description. | **PASS** |
| **TC-04** | Google Jobs (Serper) | Query Google Jobs API via Serper | `search_provider='serper'`, valid Serper key, `titles=['Staff Frontend Engineer']`, `location='Cairo, Egypt'` | Sends POST to `https://google.serper.dev/jobs`, parses Google Jobs payload with original via sources (LinkedIn, Indeed, etc.). | Parsed title, company, location, snippet, and `source='Google Jobs (via LinkedIn)'`. | **PASS** |
| **TC-05** | Google Jobs (Serper) | Error handling when Serper key is missing | `search_provider='serper'`, key is empty | Raises clear user-facing error instructing user to add key or switch to Free feeds. | Raised `ValueError: Connect a Serper Google Jobs API key in Settings, or switch to Free Search Feeds.` | **PASS** |
| **TC-06** | Settings UI | Toggle between Free, Google Jobs, and Brave providers | `PUT /api/settings` with `search_provider='serper'` and `serper_key='test-key'` | Updates database setting and returns `connections.serper=True` in bootstrap. | Saved setting and updated bootstrap status seamlessly. | **PASS** |
| **TC-07** | Ranking & Deduplication | Merge candidates from LinkedIn + feeds, deduplicate, score by CV | Multiple feeds returning overlapping URLs or titles | Deduplicates canonical URLs, ranks by relevance score descending. | Merged 253 jobs across 5 platforms (`jobicy: 48, linkedin: 18, weworkremotely: 26, arbeitnow: 146, remotive: 15`), sorted descending by match score. | **PASS** |
| **TC-08** | Tailoring Pipeline | Prepare tailored CV for an imported LinkedIn job | Axis LinkedIn job (3,460 chars) | Extracts requirements, matches against master profile, calculates coverage score. | Extracted 18 distinct requirements (React, CSS, HTML, Agile), scored against profile. | **PASS** |
| **TC-09** | Universal Web Import | Import from employer site or Wuzzuf / Indeed via JSON-LD or HTML | Public job posting URL with structured schema or semantic article markup | Extracts job title, company, location, and description fallback. | JSON-LD schema.org and HTML semantic extractors parse posting; in-place editor available for manual additions. | **PASS** |
| **TC-10** | Description Editor | In-place manual paste or edit on any imported job | Job description view -> "Edit description" | Textarea displays full text, allows editing/pasting, updates in SQLite. | PATCH `/api/jobs/{id}` updates description in place without data loss. | **PASS** |

---

## 3. Real Live Execution Evidence

### A. Live Discovery Breakdown (Executed 2026-09-05)
```text
Total discovered jobs: 253
Breakdown by platform:
  • LinkedIn Jobs: 18 (Local Cairo, Egypt + Worldwide)
  • Jobicy: 48
  • WeWorkRemotely: 26
  • Arbeitnow: 146
  • Remotive: 15
```

### B. Top Ranked Live Results Sample
1. **[jobicy]** Senior Frontend Software Engineer, Home Experience at Reddit (USA) — Score: 99%
2. **[linkedin]** Frontend Software Engineer at Axis (Cairo, Egypt) — Score: 95%
3. **[jobicy]** Senior Software Engineer, Frontend at Phantom (LATAM, Canada, Europe, USA) — Score: 92%
4. **[weworkremotely]** Senior Software Engineer at Collaboration.Ai (Remote) — Score: 91%
5. **[jobicy]** Frontend Engineering Team Lead - MarTech at Sporty Group (Europe) — Score: 91%
6. **[jobicy]** Web Frontend Engineer - JS, CSS, React, Flutter at Canonical (Anywhere) — Score: 91%

### C. Live LinkedIn Job Import & Preparation Sample
- **Target Role:** Frontend Software Engineer at Axis
- **Location:** Cairo, Egypt
- **Source:** Direct LinkedIn Guest API (`https://eg.linkedin.com/jobs/view/frontend-software-engineer-at-axis-4451761914`)
- **Extracted Description Length:** 3,460 characters
- **Tailoring Run Status:** Completed
- **Requirements Extracted:** 18 requirements parsed from LinkedIn posting.

---

## 4. Test Suite Summary
- **Python Pytest Suite:** 47 passed (100% pass rate)
- **Frontend Vitest Suite:** 11 passed (100% pass rate)
- **TypeScript Typecheck:** 0 errors
