# Jobfolio — App QA Report

Date: 2026-09-05
Target: http://127.0.0.1:8765/discover
Method: Interactive browser/computer-use testing, accessibility-tree and screenshot inspection, plus a limited source review.
Status: Testing stopped at the user's request; this report records the evidence collected up to that point.

## Summary

The main navigation, discovery pagination, job import, manual job creation, local CV generation from a complete description, and PDF/Word download triggers worked in the tested flows. However, the discovery-to-CV workflow failed for an imported job because its description contained only a short summary. Other significant problems include stale CV detail state, missing extracted qualifications, and silent loss of unsaved profile edits.

This is a broad exploratory report, not a certification that every possible case passed. Backend ownership below is a proposed investigation area unless explicitly supported by source inspection. No application was submitted, no AI operation was invoked, and no existing profile or connection configuration was saved.

**Recorded findings:** 15 issues: 6 high priority, 9 medium priority. Additional enhancements and untested scenarios are listed separately.

Priority definitions:

- **P1 — High:** blocks an important workflow, loses work, or substantially undermines correctness/accessibility.
- **P2 — Medium:** misleading behavior, recoverable failure, or meaningful usability problem.
- No P0 incident was established during this session.

## Test environment and changes made

- Existing local workspace initially contained 171 discovery results and 6 saved opportunities.
- Browser: Codex in-app browser. Explicit responsive checks: 1440 × 1000 desktop and 390 × 844 mobile; the default intermediate-width layout was also inspected.
- Imported one public job: **Web Frontend Engineer - JS, CSS, React, Flutter at Canonical**.
  - Job ID: `a74cfc6ca9e94b6884cb238d9a29566b`.
  - Its local CV preparation failed.
- Created one clearly labeled synthetic job: **QA TEST — Frontend Engineer — 2026-09-05**, company **QA Test Fixture**.
  - Job ID: `d9dc234715f64adda79503198caa5006`.
  - Complete description supplied locally; no posting URL.
  - Generated a local CV with 50% provisional coverage.
  - Triggered its PDF and Word downloads successfully.
- Ran one new discovery search. The search button entered a disabled “Searching feeds…” state and later returned to normal; the visible result count remained 171. Per-provider success was not established.
- Temporarily edited the profile headline without saving, then navigated away. Returning showed the original headline.
- End-of-test saved opportunity count was 8. The added jobs and generated test documents were left in place for inspection; no cleanup deletion was performed.
- Testing stopped immediately when requested. The last captured page was `/discover?page=999`; navigation to `/discover?page=abc` had been issued but its rendered result was not inspected. The desktop viewport override had not yet been reset.

## Findings at a glance

| ID | Priority | Finding | Proposed owner |
|---|---|---|---|
| QA-01 | P1 | Imported job has a truncated description; local CV preparation fails | BE ingestion + FE recovery |
| QA-02 | P1 | CV detail remains stale after successful generation | FE query/state synchronization |
| QA-03 | P1 | Local requirement audit omits explicit preferred qualifications | BE extraction + FE review |
| QA-04 | P1 | Unsaved profile edits disappear without a warning | FE forms/navigation |
| QA-05 | P1 | Application links lose link semantics through `role="listitem"` | FE accessibility |
| QA-06 | P1 | Invalid pagination URL hides all results and removes pagination recovery | FE routing/pagination |
| QA-07 | P2 | Leading/trailing whitespace prevents search matches | FE filtering |
| QA-08 | P2 | No-match discovery state claims there are no discovered jobs | FE empty states |
| QA-09 | P2 | HTML entities and encoded markup appear in user-facing job content | BE normalization + FE rendering |
| QA-10 | P2 | Posting source labels misidentify feed and manually pasted jobs | BE metadata + FE labels |
| QA-11 | P2 | CV operation error leaks into unrelated pages | FE operation state |
| QA-12 | P2 | Failed CV preparation still leaves “Ready to prepare” status | BE job/run status + FE status display |
| QA-13 | P2 | Historical failures expose raw validation internals | BE error mapping + FE messaging |
| QA-14 | P2 | Opportunity filters do not expose their selected state | FE accessibility |
| QA-15 | P2 | Existing workspace still receives first-use empty/onboarding copy | FE conditional copy |

## Detailed findings

### QA-01 — Imported job cannot complete the local CV workflow

**Priority:** P1. **Evidence:** reproduced through the UI.

**Location:** Discover → Canonical result → Import → Job description → Prepare local CV.

**Steps:**

1. Filter Discover for `Canonical`.
2. Import **Web Frontend Engineer - JS, CSS, React, Flutter**.
3. Inspect “About this role.”
4. Click **Prepare local CV** and open the Tailored CV tab.

**Actual:** The description consists of the same short company summary shown in Discover, ending mid-word at `publ`. Preparation fails with: “No requirements could be identified. Add a complete description with requirements, or connect AI extraction.” There is no visible description-edit or replacement action on the job page.

**Expected:** Import should obtain a complete usable description, or clearly mark the import as incomplete and offer an immediate way to paste/replace it before preparation.

**Impact:** A core advertised path—discover, import, tailor—ends in a dead end for this job. AI extraction cannot be assumed to recover requirements that were never ingested.

**Recommendations:**

- BE: inspect importer fallback behavior; store full description separately from the display snippet, with extraction status and provenance.
- BE: require an adequate description before queuing preparation; distinguish unavailable description from extraction failure.
- FE: add “Edit/paste full description” and “Retry fetching description” actions, preserving the saved job.

**Acceptance:** The same job either has its complete responsibilities/qualifications after import or displays an actionable incomplete-description state. A user can repair it in place and successfully retry.

### QA-02 — Generated CV is visible in the library but absent from its detail page

**Priority:** P1. **Evidence:** reproduced; hard reload resolved it.

**Steps:**

1. Create the synthetic job using the full description in the fixture section below.
2. Click **Prepare local CV**.
3. Navigate to **CV library**; observe the test CV at **50% coverage**.
4. Click its **Review** link.

**Actual:** The detail page still shows **Saved**, **Prepare local CV**, and **Start with your tailored CV**, despite the generated artifact being present in the library. A subsequent observation remained stale. Reloading changed it to **Needs review**, **Rebuild local CV**, and the populated preview.

**Expected:** All views converge on the completed operation without manual reload.

**Impact:** Users may believe generation failed, rerun it unnecessarily, or be unable to review the result.

**Recommendations:** FE: invalidate/refetch job-detail and workspace queries on completion, not only on enqueue; inspect polling subscription lifetime when leaving a running job; derive operation state consistently.

**Acceptance:** Start generation, immediately navigate elsewhere, then return via CV library. The completed preview and status appear automatically, without duplicate generation or reload.

### QA-03 — Explicit preferred qualifications are missing from the coverage audit

**Priority:** P1. **Evidence:** reproduced with controlled input.

**Input includes:** `Preferred qualifications: Next.js, automated testing, and web accessibility.`

**Actual:** The generated audit contains only two requirements: the responsibilities line and the required-qualifications line. The preferred-qualifications line is absent, even though the legend explicitly shows **Required ×3 · Preferred ×1**. The generated score is 50%, based on two partially supported required items.

**Expected:** Explicit preferred criteria appear in the audit and receive the appropriate weight. Multiple independent skills should be reviewable at useful granularity.

**Impact:** The coverage percentage excludes declared job criteria, making the denominator incomplete. A “reviewed every requirement” acknowledgement cannot compensate for invisible omissions.

**Recommendations:** BE: handle explicit preferred headings and common bullet/paragraph formats; preserve source spans; split compound requirements carefully. FE: show the extraction count and offer a way to report/add missing requirements before approval.

**Acceptance:** The test fixture includes all declared required and preferred qualifications in the audit. Required/preferred classification and score weighting are deterministic and explainable.

### QA-04 — Profile edits are silently lost on navigation

**Priority:** P1. **Evidence:** reproduced; persisted profile stayed unchanged.

**Steps:** Open My profile → change Headline to `QA UNSAVED EDIT` → click Applications → return to My profile.

**Actual:** Navigation succeeds without an in-app warning or browser confirmation. The original headline is restored, and the edit is lost.

**Expected:** Warn before discarding dirty form changes, or retain a clearly indicated local draft.

**Impact:** Users can lose substantial profile editing work by following normal navigation.

**Recommendations:** FE: track form dirtiness, provide Save/Discard/Stay handling for internal navigation, and handle reload/close appropriately. Extend the same policy to other long editing forms.

**Acceptance:** A modified profile cannot be silently discarded through sidebar navigation, browser back, reload, or closing the tab. Discard must be explicit, or a draft must be recoverable.

### QA-05 — Application rows are clickable links but announced as list items

**Priority:** P1. **Evidence:** browser DOM/accessibility inspection plus source confirmation.

**Location:** `frontend/src/pages/applications/ApplicationsPage.tsx`.

**Actual:** Application rows navigate when clicked, but the accessibility tree exposes their text without link semantics. DOM inspection showed an anchor with `role="listitem"`; the source assigns that role directly to the React Router `Link`.

**Expected:** Each list item contains a semantic link, discoverable through screen-reader link navigation.

**Impact:** Assistive-technology users cannot reliably identify the row as a navigation action. This is a role/semantics issue; a keyboard trap was not established.

**Recommendation:** Render `<ul><li><Link ...>...</Link></li></ul>` or equivalent semantic structure; do not override the anchor's role with `listitem`. Relevant accessibility principle: programmatically expose the correct role and relationships.

**Acceptance:** All tracker rows are exposed as links within list items, are keyboard reachable, and activate with Enter.

### QA-06 — Out-of-range pagination URL shows an unrecoverable empty list

**Priority:** P1. **Evidence:** `/discover?page=999` reproduced in browser; limited source review supports the cause.

**Actual:** The page says **Discovered results 171**, then **No discovered jobs yet**. No Previous/Next controls appear.

**Expected:** Clamp to a valid page or redirect to page 1 while keeping results available.

**Source evidence:** `DiscoverPage.tsx` clamps only the lower bound with `Math.max(1, parseInt(...))`; it does not clamp to `totalPages`. Pagination controls are rendered only when the current slice has items. Nonnumeric handling also needs a finite-number guard, but the `page=abc` browser result was not inspected before testing stopped.

**Impact:** Stale/shared/edited URLs can hide the entire collection and provide the wrong recovery action.

**Recommendation:** Normalize finite positive integer page input, clamp both bounds after filtering, update the URL, and distinguish invalid pagination from empty results.

**Acceptance:** Test `page=999`, `0`, `-1`, `abc`, an empty value, decimals, and a page that becomes invalid after the result count shrinks. Each resolves to a usable valid page.

### QA-07 — Search does not trim whitespace

**Priority:** P2. **Evidence:** reproduced in Discover and Opportunities.

**Steps:** In Discover compare `reddit` with `  reddit  `. In Opportunities, use To review and filter for `  Reddit  `.

**Actual:** `reddit` finds 2 discovery results; surrounding spaces produce 0. The padded Opportunities query also produces an empty state despite a matching Reddit job.

**Expected:** Leading/trailing whitespace is ignored for ordinary text filtering.

**Source evidence:** Discover lowercases the query but does not trim it before substring matching.

**Recommendation:** Normalize filter terms with trimming and a consistent case-folding policy; consider whitespace-only input equivalent to an empty query.

**Acceptance:** `Reddit`, `reddit`, and padded variants find the same records; keyboard clearing restores the complete list.

### QA-08 — No-match discovery copy incorrectly implies no data exists

**Priority:** P2. **Evidence:** reproduced.

**Steps:** Filter Discover for `zzzxq-no-results-qa`.

**Actual:** “No discovered jobs yet” and **Find opportunities now**, while the workspace has 171 discovered results.

**Expected:** “No results match your filter” with **Clear filter**, preserving a separate first-use empty state.

**Impact:** Encourages unnecessary feed searches and hides the direct solution.

**Recommendation:** FE: model never-searched, no feed results, no local matches, failed search, and invalid pagination as distinct states.

**Acceptance:** An unmatched local query offers a working clear action and never claims the underlying collection is empty.

### QA-09 — Encoded HTML leaks into titles and summaries

**Priority:** P2. **Evidence:** visible in multiple pages.

**Examples:**

- Discover → **Software Engineer at Yext** shows `&lt;div class=&quot;content-intro&quot;&gt;&lt;p&gt;...` in the summary.
- Opportunities/CV library/Applications show titles such as `Senior Frontend Engineer &amp;#8211; Contract` and `Senior Software Engineer &amp;#8211; MAAS`.
- A Gusto summary includes `&nbsp;`.

**Expected:** Clean human-readable titles and summaries, with a real dash/space and no markup fragments.

**Impact:** Reduces trust and readability and may contaminate exported/generated content.

**Recommendations:** BE: normalize entity encoding and extract plain-text summaries at ingestion, including legacy-data repair. FE: keep rendering safe; do not solve this by blindly injecting HTML.

**Acceptance:** Representative Jobicy, Arbeitnow, and WeWorkRemotely inputs render readable text without exposing markup or permitting executable content.

### QA-10 — Source labels are misleading

**Priority:** P2. **Evidence:** reproduced.

**Actual:** The Canonical Jobicy import says **Source: Employer website**. The synthetic pasted description, which has no URL at all, also says **Employer website**. Discovery cards display **Manual** for records obtained from public feeds.

**Expected:** Distinguish content source, discovery provider, and application method. A manual application method is not a content-source label.

**Impact:** Users cannot tell where data came from or understand whether they are viewing original employer content, a feed copy, or pasted text.

**Recommendations:** BE: store separate provider/source/application-method fields. FE: label the relevant concept explicitly; use **Pasted description** for the fixture and **Jobicy feed** where appropriate.

**Acceptance:** Manual entry, feed discovery, and direct employer import display accurate provenance consistently across list and detail views.

### QA-11 — A job-operation error persists on an unrelated page

**Priority:** P2. **Evidence:** reproduced.

**Steps:** Trigger the Canonical local-preparation failure, then navigate to Opportunities.

**Actual:** The same requirements error appears at the top of Opportunities without naming the affected job. It remained until manually dismissed.

**Expected:** Scoped contextual error or a global notification that identifies the operation/job and links to recovery.

**Impact:** Makes the destination page look broken and obscures which action failed.

**Recommendation:** FE: associate operation errors with job/run IDs, scope their presentation, and avoid duplicate nested alerts. Retain failure history separately from current-page validation.

**Acceptance:** Navigation does not show an ambiguous error on unrelated content. A retained global error names the job and offers a relevant retry/repair link.

### QA-12 — Preparation failure is not reflected in the opportunity's readiness label

**Priority:** P2. **Evidence:** reproduced.

**Actual:** After the Canonical requirements failure, its Opportunities row still says **Saved · Ready to prepare**.

**Expected:** A useful status such as **Needs full description** or **Preparation failed**, with recovery available.

**Impact:** The list gives no indication that the next action will repeat a known failure.

**Recommendation:** Separate job lifecycle from latest preparation status. Preserve a structured failure reason and surface it alongside the job state.

**Acceptance:** Failed jobs show an actionable status; repairing the input and completing preparation clears it automatically.

### QA-13 — Application activity exposes raw internal validation errors

**Priority:** P2. **Evidence:** observed in pre-existing history; the underlying AI failure was not reproduced in this session.

**Actual:** Applications shows a historical error containing `1 validation error for Rewrites`, `Invalid JSON`, `input_value='User Safety: safe'`, and a Pydantic documentation URL.

**Expected:** A concise explanation such as “The AI provider returned an invalid response. Your previous CV is unchanged,” plus an appropriate retry path. Technical detail belongs behind a diagnostic disclosure or in local logs.

**Impact:** Exposes implementation detail without telling the user how to recover.

**Recommendations:** BE: map provider/validation exceptions to structured public errors; validate responses and apply bounded retry/fallback behavior. FE: display job-specific recovery, keeping diagnostics optional.

**Acceptance:** Malformed provider output cannot become the primary user-facing error or overwrite a valid package. Historical errors identify the affected job and distinguish resolved from active failures.

### QA-14 — Selected opportunity filters have no accessible state

**Priority:** P2. **Evidence:** UI and DOM inspection.

**Actual:** All jobs / To review / Approved / Skipped work visually, but inspection of the selected Skipped button found both `aria-pressed` and `aria-selected` absent. The accessibility tree exposes ordinary buttons without a selected state.

**Expected:** The active filter is programmatically identifiable.

**Recommendation:** Use an appropriate toggle-button or tab pattern with accessible selected state and consistent keyboard behavior.

**Acceptance:** Screen-reader users can identify the active filter independently of focus or color, and filtered result-count changes are understandable.

### QA-15 — First-use copy remains after the workspace is populated

**Priority:** P2. **Evidence:** observed/reproduced.

**Examples:**

- Opportunities says **Ready for your first search** despite 171 discovery results and several saved jobs.
- An empty Skipped/filtered view offers **Add your first job** despite 8 existing opportunities.

**Expected:** Copy reflects workspace progress and distinguishes an empty filtered view from an empty workspace.

**Recommendation:** Derive onboarding completion from actual data and use context-specific empty actions, such as **Show all jobs** or **Clear filter**.

**Acceptance:** Populated workspaces do not display first-job/first-search prompts in filtered views.

## Missing parts and enhancement backlog

These are observed product gaps or improvement proposals, not additional confirmed defects. Product intent should determine which are requirements.

| Area | Observed gap / proposed enhancement | FE work | BE work / investigation |
|---|---|---|---|
| Discovery controls | Only a free-text filter and Previous/Next controls were visible | Add location eligibility, remote scope, source, score, date, and saved-state filters; sorting and clear-all | Normalize filterable metadata; support scalable queries if the collection grows |
| Match explanation | 99% skill match appears for a USA role while the preference is Egypt; ranking describes keyword/role alignment | Separate skill relevance from location/work-authorization compatibility; show why a match ranked highly | Preserve region restrictions and reasons; do not infer legal eligibility |
| Job freshness | Discover does not show posting age/last-check details on cards | Show published/fetched/last-verified dates and stale/expired states | Track provider timestamps, expiry, and verification outcome |
| Search diagnostics | Search returns from loading, but no per-feed completion report was visible on Discover | Show last-run time, new/duplicate result counts, partial success, and actionable failures | Store per-source outcomes, bounded timeouts, retries, and rate-limit state |
| Import progress | All Import buttons became disabled while one job imported, without per-row loading text | Show progress on the active row and a clear completion/error message | Enforce idempotency and return stable operation identifiers |
| Mobile navigation | At 390px the top navigation is a horizontally scrolling strip with clipped items | Consider a clear menu/drawer or stronger overflow affordance; preserve active-location context | None required |
| Touch targets | At 390px, sampled Import buttons were 33px high, Run new search 40px, Refresh 26×26px | Increase effective hit areas toward 44×44px where practical | None required; this alone does not establish a WCAG AA failure |
| CV library | No visible search, sorting, version history, or comparison controls | Add search, generation time, package version, and current/approved indicators | Preserve immutable versions and provenance |
| Application tracking | No visible search/status filtering or next-action/reminder controls | Add filters, next action, notes, and appropriate outcome states | Model lifecycle transitions and retain history |
| Manual outcome | Outcome form defaults to “I confirmed the application was submitted” | Consider an explicit unselected initial choice to reduce accidental status changes | Validate legal transitions; store evidence and audit timestamps |
| Review granularity | Compound requirement sentences receive one rating | Allow atomic criteria, multiple evidence snippets, and missing-criterion feedback | Improve segmentation and evidence mapping |
| History readability | Events show dates without precise time; global activity lacks clear job context | Show time and job links, filters, collapsible diagnostics | Preserve event correlation/run identifiers |
| Profile editing | Repeated fields/actions have labels such as Entry 1 / Add evidence across sections | Include section context in accessible names, improve long-form navigation, add draft recovery | Consider versioning and rollback for profile changes |
| Connection status | “Connected” was visible, but live provider health was not verified | Distinguish key saved, configuration valid, and last successful request; offer an explicit test action | Add a non-destructive health check with clear cost/data behavior |
| AI disclosure consistency | Settings says CV text is sent only on “Tailor with AI”, while profile has a separate “Review & Structure with AI” action | Make disclosures accurately cover every AI action before use | Verify redaction consistently across tailoring, structuring, and cover-letter flows |
| Recovery/backup | No backup/restore or test-data cleanup path was established | Provide discoverable export/restore and safe archival where intended | Backup local database/documents with integrity and schema-version checks |

## Executed coverage matrix

“Pass” means the stated observation passed, not that the whole feature is certified.

| Case | Result | Evidence / limitation |
|---|---|---|
| Initial Discover load | Pass | 171 results and populated navigation |
| Exact/company text filtering | Pass | Reddit → 2; Canonical → 5 |
| Case-insensitive filtering | Pass | `Reddit` and `reddit` matched |
| Whitespace-padded query | Fail | QA-07 |
| No-match filter recovery | Fail | QA-08 |
| Query reload persistence | Pass | `reddit` retained after reload |
| Clear filter with keyboard | Pass | Ctrl+A, Backspace restored 171 results |
| Filter from page 2 | Pass | Canonical results reset to the first page |
| Traverse pages 1–7 | Pass | Correct ranges; final range 151–171 |
| First/last page button boundaries | Pass | Previous disabled on first; Next disabled on last |
| Previous-page navigation | Pass | Page 7 → page 6 |
| Out-of-range page 999 | Fail | QA-06 |
| Nonnumeric page abc | Not evaluated | Navigation issued before stop; no rendered result captured |
| Script-like filter text | Limited pass | Literal `<script>alert(1)</script>` displayed as text; no dialog observed; not a security audit |
| New feed search loading state | Pass | Button disabled as Searching feeds… |
| New feed search per-provider success | Unverified | Button recovered; result count stayed 171 |
| Public job import | Partial | Saved job and count updated, but incomplete description: QA-01 |
| Already-saved UI after import | Pass | Imported Canonical result changed to Already saved/Open job |
| Import duplicate prevention at API level | Unverified | Only UI deduplication checked |
| Open imported job | Pass | Correct job detail and review tabs |
| Blank import URL | Pass | Native required validation blocked submission |
| Malformed import URL | Pass | Native URL validation: “Please enter a URL.” |
| Switch link/paste add modes | Pass | Both modes accessible; current URL carried across modes |
| Required manual job title | Pass | Native “Please fill out this field.” validation |
| Save complete pasted job without URL | Pass | Synthetic job persisted |
| Prepare imported short-description job | Fail | QA-01 |
| Prepare complete synthetic job locally | Pass | CV appeared in library at 50% |
| Generated detail refresh without reload | Fail | QA-02 |
| Generated detail after reload | Pass | Preview and Needs review state appeared |
| Required/preferred extraction completeness | Fail | QA-03 |
| Expand requirement evidence | Pass | Job quote and CV evidence displayed |
| CV review save before acknowledgement | Pass | Save CV review disabled |
| Coverage save before acknowledgement | Pass | Save coverage review disabled |
| Approval before review prerequisites | Pass | Approve this package disabled |
| Manual outcome form opening | Pass | Outcome selection and confirmation-details field displayed |
| Manual outcome submission | Not tested | No false application outcome recorded |
| Job activity navigation | Pass | Import/save and operation events displayed |
| CV library navigation | Pass | Generated and existing documents listed |
| Word download trigger | Pass | Browser download event received |
| PDF download trigger | Pass | Browser download event received |
| Export content/layout integrity | Not tested | Download events do not prove document quality |
| To review filter | Pass | Test job and Reddit displayed |
| Approved filter | Pass | Existing approved Roofr job displayed |
| Skipped empty view | Partial | Filter worked; first-job copy incorrect |
| Filter selected-state accessibility | Fail | QA-14 |
| Application row click navigation | Pass | Opened test job Application tab |
| Application row link semantics | Fail | QA-05 |
| Search preferences page | Inspection only | Titles/location/exclusions/salary/authorization controls present |
| AI settings and search-source tabs | Inspection only | Configuration displayed; no credentials/settings changed |
| Profile form initial rendering | Pass | Personal and evidence fields visible |
| Unsaved profile navigation | Fail | QA-04 |
| Desktop layout at 1440px | Limited pass | Screenshot visually usable; no full contrast/performance audit |
| Mobile layout at 390px | Partial | Usable content; scrolling navigation and small hit areas |
| Mobile Discover page overflow | Pass for sample | Document width did not exceed viewport |
| Console error sample | Pass for sample | Captured error/warn log request returned none; not a complete historical guarantee |

## Evidence fixture

Synthetic title: `QA TEST — Frontend Engineer — 2026-09-05`
Company: `QA Test Fixture`
Location: `Remote — Egypt`
Posting URL: empty.

```text
QA TEST DATA. This is a synthetic job for local testing only. Do not apply.
Responsibilities: Build accessible React interfaces and maintain TypeScript applications. Write unit tests and integrate REST APIs.
Required qualifications: Experience with React, TypeScript, JavaScript, HTML, CSS, Git, and REST APIs.
Preferred qualifications: Next.js, automated testing, and web accessibility.
Location: Remote, Egypt.
```

## FE/BE implementation plan

### First: repair core workflow correctness

1. **BE ingestion + FE recovery:** fix QA-01 and retain full descriptions/provenance. Provide in-place repair.
2. **FE asynchronous state:** fix QA-02, QA-11, and QA-12 together so job, run, library, and detail state agree.
3. **BE extraction:** add the fixture above as a meaningful regression case for QA-03, including preferred criteria and atomic requirement handling.
4. **FE data preservation:** implement unsaved-edit protection for QA-04.
5. **FE accessibility/routing:** correct application link semantics and pagination normalization, QA-05/QA-06.

### Next: improve usability and trust

6. Normalize filters and distinguish empty states, QA-07/QA-08/QA-15.
7. Normalize imported text and source labels, QA-09/QA-10.
8. Map structured operation errors into useful messages, QA-13.
9. Add accessible filter states, QA-14, and improve mobile hit areas.
10. Add discovery diagnostics/freshness, document versions, and richer application tracking according to product priorities.

Suggested frontend follow-up sequence: `$impeccable harden` for recovery and dirty forms; `$impeccable clarify` for source/error/empty-state copy; `$impeccable adapt` for mobile controls; `$impeccable audit` after fixes; `$impeccable polish` last. These can be run individually or in a chosen order.

## Important scenarios still untested

The user stopped testing before these could be exercised. They must not be interpreted as passing or as confirmed missing implementations.

- New/empty workspace onboarding and missing master CV.
- Profile save, required-field limits, invalid email/phone formats, whitespace-only fields, long/multilingual evidence, and draft recovery after restart.
- Master CV upload/replacement, wrong formats, oversized/corrupt files, scanned PDFs, parsing failures, and original-file immutability.
- AI connectivity, invalid/revoked keys, provider timeouts, malformed/partial responses, fallback behavior, rate limits, billing classification, and redaction.
- Cover-letter generation and profile AI structuring.
- Save/reload persistence of changed preferences, exclusion enforcement, automatic scheduling, remote/location semantics, and salary handling.
- Search cancellation, partial provider outages, offline behavior, repeated concurrent searches, changing preferences during a run, and restarting mid-run.
- Backend URL validation, redirect handling, SSRF protections, supported/unsupported ATS imports, missing/expired postings, and canonical URL deduplication.
- Completed review save/restore, rating updates, package approval, rebuild invalidation, and exact-package binding.
- Real application submission, Greenhouse/Lever adapters, external login/CAPTCHA handoff, uncertain submission, duplicate prevention, and manual outcome transitions.
- Skip/unskip, archive/restore, deletion, and cleanup of test records.
- Document byte/content validation, PDF visual layout, Word layout, page breaks, selectable text, export accessibility, and artifact-version consistency.
- Additional screen sizes, full keyboard traversal, screen-reader testing, focus restoration, zoom/text scaling, reduced motion, contrast, and theme behavior.
- API authorization/origin controls, concurrency, database integrity, migration/backup/restore, storage limits, and load/performance tests.
- Arbitrary missing routes/job IDs and direct-link recovery beyond the tested pagination case.

## Audit confidence and limitations

- Findings are grounded in interactive observations unless marked as historical, source-supported, proposed, or untested.
- Backend code, database state, and API traffic were not audited. The limited source review covered Discover and Applications, plus a mechanical detector pass over four frontend page files.
- The Impeccable detector returned `[]` for those files. That is not a clean bill of health: it does not detect the reproduced behavioral issues above.
- Accessibility and responsive behavior were sampled. Performance, theming, full contrast compliance, and complete implementation integrity were not measured, so a numeric overall audit score would be misleading and is intentionally omitted.
- Screenshots were inspected in the session; this Markdown records textual reproduction evidence and does not claim to include a separate screenshot archive.
- Some automation-level empty-fill attempts did not clear controlled fields; keyboard selection/deletion succeeded. These tool-specific attempts were not reported as app defects.

## Tooling note

The Impeccable context check reported an unused top-level `note` key in `.impeccable/config.local.json`. This is a tooling configuration observation, not an app defect. Removing that unused key is optional and was not performed.
