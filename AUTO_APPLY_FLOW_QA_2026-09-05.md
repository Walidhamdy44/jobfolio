# Automatic application flow — QA findings

Date: 2026-09-05
Application: Jobfolio, local workspace
Job: **Senior Frontend Engineer - Web — MBC GROUP**
Job ID: `ddf6a0b01ed74ede8953e7fd43c066e5`

- [Local job](http://127.0.0.1:8765/jobs/ddf6a0b01ed74ede8953e7fd43c066e5/description)
- [Application flow](http://127.0.0.1:8765/jobs/ddf6a0b01ed74ede8953e7fd43c066e5/application)
- [LinkedIn posting](https://www.linkedin.com/jobs/view/senior-frontend-engineer-web-at-mbc-group-4459732169/)

## Conclusion

**Full Auto-Apply is not ready for unattended real applications.** The inspected implementation can launch without reviewed/approved content, generate unsupported applicant answers, and mark a submission successful without verifying employer confirmation. Co-Pilot also needs a durable browser handoff and accurate completion reporting.

For this specific job, Jobfolio's history shows repeated failures to find an application button. In the browser used for this audit, the same posting had an enabled **Easy Apply to this job** button. Clicking it opened **Apply to MBC GROUP**, **1/4 pages**, **Contact info**. Therefore, the error does not establish that the job is closed. The precise difference between the app's persistent browser session and the audit browser remains unverified.

This report contains **21 findings**, with evidence levels distinguished below. It does not claim that a real agent application completed end to end.

## Scope, actions, and evidence

### Performed

- Opened the specified job in the in-app browser.
- Inspected Description, Application, and Activity & History.
- Checked Co-Pilot and Full Auto-Apply mode presentation; restored Co-Pilot to checked.
- Opened the actual LinkedIn posting and inspected its enabled Apply control.
- Opened the first Easy Apply modal without entering data or clicking Next.
- Reviewed the relevant frontend, API handler, browser worker, and answer-engine source.
- Ran 16 isolated behavior probes with mocked browser/queue/storage boundaries and temporary files.
- Ran the repository's existing auto-apply tests: **6 passed, 2 deprecation warnings**.

### Not performed

- Did not click Jobfolio's live Launch Auto-Apply button. The current engine can upload a CV and fill unsupported answers before a human review point; the critical behavior was instead exercised through isolated probes.
- Did not submit a real application, upload a CV, enter new applicant data into LinkedIn, invoke external AI, change credentials, or change the saved job/package.
- Did not advance beyond the first LinkedIn page or inspect the remaining three pages.
- Did not establish which account/session the app's separate persistent browser currently uses.

### Evidence labels

- **UI:** observed through browser interaction in this session.
- **History:** a previous run's event was observed; that run was not re-executed.
- **Probe:** reproduced against local functions/API with synthetic data and mocked side effects.
- **Source:** direct implementation finding; the live scenario was not executed.

Severity:

- **P0 — Release blocker:** could send unapproved/false data or record a false/unsafe submission outcome. This label identifies a release risk, not a claim that harm occurred.
- **P1 — High:** blocks or materially undermines the agent workflow.
- **P2 — Medium:** confusing or incomplete UX, diagnostics, or semantics with a workaround.

## Finding index

| ID | Severity | Finding | Evidence |
|---|---|---|---|
| AA-01 | P1 | App cannot find Apply although the posting currently exposes Easy Apply | UI + History |
| AA-02 | P0 | Auto-Apply bypasses package review/approval enforcement | Probe + Source |
| AA-03 | P0 | Work authorization, sponsorship, and consent answers are guessed | Probe + Source |
| AA-04 | P1 | Experience and availability answers are hard-coded | Probe + Source |
| AA-05 | P1 | Salary resolver crashes and misinterprets units/question types | Probe + Source |
| AA-06 | P1 | Dropdown matching can convert unknown answers into arbitrary choices | Probe + Source |
| AA-07 | P0 | Clicking submit is treated as confirmed submission | Probe + Source |
| AA-08 | P0 | Errors after submit are downgraded to Needs input instead of Uncertain | Probe + Source |
| AA-09 | P1 | Co-Pilot has no durable browser handoff | Source |
| AA-10 | P1 | Missing form/upload can still produce a successful prefill message | Probe + Source |
| AA-11 | P1 | Early termination/browser-launch failure can leave Submitting stuck | Probe + Source |
| AA-12 | P1 | Uploads select the first file input and swallow failures | Source |
| AA-13 | P1 | Filled answers are not bound to the approved package | Source |
| AA-14 | P1 | Existing field values and phone-country selectors are mishandled | UI + Source |
| AA-15 | P1 | Auto-Apply omits the standard adapter's form/challenge checks | Source |
| AA-16 | P1 | External Apply assumes a popup; redirects/session state are weakly handled | Source |
| AA-17 | P1 | Generic AI answers lack the candidate evidence needed for truthfulness | Source |
| AA-18 | P2 | UI says manual-only while offering automatic submission | UI + Source |
| AA-19 | P2 | Missing Apply is mislabeled as an incomplete description | UI + Source |
| AA-20 | P2 | Review checklist states are hidden from accessibility output | UI + Source |
| AA-21 | P1 | Existing tests encode guessed answers and miss submission safeguards | Tests + Source |

## Detailed findings

### AA-01 — Apply discovery/session failure on an active Easy Apply posting

**P1 · UI + History · BE browser adapter / FE diagnostics**

**Observed:** Jobfolio shows **Needs your input** and “No active application button was found on this posting. Verify the job is still open.” History contains repeated sequences of launching, navigating, searching for the button, and failing. It also contains a manual “not submitted” record.

In the audit browser, opening the same URL redirected from `eg.linkedin.com` to `www.linkedin.com` and exposed an enabled button with accessible name **Easy Apply to this job**, text **Easy Apply**. Clicking it opened the real four-page form.

**Expected:** Recognize the available control in the agent's authenticated browser, or identify the exact blocker: login required, session unavailable, challenge, delayed rendering, selector mismatch, or genuinely closed posting.

**Important uncertainty:** This does not prove the button was visible in the app's separate persistent profile at the time of its failed runs. The current button's text would match the code's `:has-text("Easy Apply")` fallback; changing selectors alone is not an established fix.

**Fix:** Record final URL, detected login/challenge state, screenshot, visible candidate buttons, and run/session identity on failure. Use semantic visible locators and condition-based waits rather than selecting `.first` after fixed sleeps. Offer **Open this exact agent session** from the failure state.

**Acceptance:** Reproduce using the same persistent profile; identify the real blocker, then open the MBC GROUP Easy Apply modal without an ambiguous closed-job warning. Test logged-in, logged-out, delayed, challenged, and closed-posting states separately.

**Source:** [backend/browser.py:259](/D:/WORK/agent-jobs/backend/browser.py:259).

### AA-02 — Full-auto accepts an unreviewed, unapproved package

**P0 · Probe + Source · BE enforcement + FE gating**

**Probe:** The isolated endpoint test supplied a package with `approved=False`, `cv_reviewed=False`, and `coverage_reviewed=False`, then posted `auto_submit=True`. The endpoint returned **HTTP 200** and enqueued a synthetic run. Storage and queue boundaries were mocked; no real run executed.

**Source:** `/auto-apply` checks busy state and package existence, but not review flags, approval hash, answers, or file integrity. The worker only checks that a package and PDF path exist. In contrast, the standard `/submit` route verifies approval/hash and uses the reviewed package.

The frontend Launch button checks `isLocked`, pending state, and package existence. It does not require review completion or clean drafts. `handleAutoApply` conditionally auto-approves an already-reviewed package, then invokes auto-apply even when that approval condition is false.

**Impact:** The separate agent path defeats the product's exact-package approval boundary.

**Fix:** Require explicit approval bound to an immutable package hash and reviewed answers at the API boundary. Separate draft preparation from employer submission. Reject unreviewed, changed, missing, or stale packages independently of UI controls. Do not implicitly approve inside Launch.

**Acceptance:** Unapproved/unreviewed/stale packages are rejected before browser launch or uploads. A successful request records the exact approved package and answer version used.

**Sources:** [backend/app.py:437](/D:/WORK/agent-jobs/backend/app.py:437), [JobApplicationPage.tsx:91](/D:/WORK/agent-jobs/frontend/src/pages/jobs/JobApplicationPage.tsx:91).

### AA-03 — The engine invents eligibility and consent answers

**P0 · Probe + Source · BE answer engine**

**Probe results:**

- Missing work authorization → **Yes** to legal authorization in the US.
- Explicit preference “Not authorized to work in the US” → still **Yes**.
- Missing sponsorship preference → **No**.
- No connected provider and a question containing “I agree to the terms” → **Yes** from the fallback resolver. This probe used a synthetic text field; the actual checkbox path is separate.

The radio handler checks radio labels containing `yes`, `agree`, `confirm`, or `authorized` without considering the actual question, mutually exclusive group meaning, or evidence. It could also match text containing “not authorized.”

**UI contradiction:** The job page warns “Work authorization is not set; answer any related questions yourself,” but the engine supplies those answers.

**Fix:** Return an explicit unresolved state for authorization, sponsorship, consent, clearance, or any unsupported answer. Require user-supplied facts, jurisdiction/context, and deliberate consent. Never infer answers by choosing Yes-like options.

**Acceptance:** Missing or contradictory facts stop the flow with the exact question shown. Consent is never synthesized. Tests cover negation and opposing radio options.

**Sources:** [form_engine.py:61](/D:/WORK/agent-jobs/backend/form_engine.py:61), [form_engine.py:286](/D:/WORK/agent-jobs/backend/form_engine.py:286), [browser.py:372](/D:/WORK/agent-jobs/backend/browser.py:372).

### AA-04 — Experience and start-date answers are hard-coded

**P1 · Probe + Source · BE answer engine**

**Actual:** An empty profile returns **5** years of React experience. Other technologies have fixed values. A missing notice-period preference returns **Immediately / 2 weeks**.

The function builds a text corpus but does not use it to determine the returned experience duration.

**Expected:** Use explicit verified facts or ask the user. Total career length is not necessarily experience with a specific technology; start dates are personal commitments.

**Fix:** Store structured, reviewed experience/availability facts; avoid arbitrary duration defaults and ambiguous combined answers.

**Acceptance:** Empty profiles produce unresolved answers, not five years or an immediate start. Every generated factual answer has evidence or explicit user input.

**Sources:** [form_engine.py:83](/D:/WORK/agent-jobs/backend/form_engine.py:83), [form_engine.py:161](/D:/WORK/agent-jobs/backend/form_engine.py:161).

### AA-05 — Salary resolution has both runtime and interpretation failures

**P1 · Probe + Source · BE answer engine**

**Reproduced:**

| Input | Actual |
|---|---|
| Annual salary; job location `Cairo`; no preference | `UnboundLocalError` for `loc` |
| Annual salary; job location `Berlin`; no preference | Same exception |
| Monthly salary; preference `EGP 65000 per month` | `5416` |
| Question `Expected start date`; remote job | `85000` |

**Cause:** `loc` is defined only in the monthly branch but read in the annual branch. Amount-size heuristics infer pay period, and broad tokens such as `expected`, `desired`, and `rate` classify unrelated questions as salary questions. Currency is not modeled explicitly. Location-based salaries are guessed when preferences are absent.

**Impact:** Fields can be left blank after swallowed exceptions or populated with materially wrong amounts/types.

**Fix:** Use structured currency/amount/period preferences, precise question classification, validated unit conversion, and an unresolved state when facts are missing.

**Acceptance:** The four cases above no longer crash or invent values. Add annual/monthly/hourly, decimals, ranges, currency, and ambiguous-note cases.

**Source:** [form_engine.py:110](/D:/WORK/agent-jobs/backend/form_engine.py:110), especially [line 156](/D:/WORK/agent-jobs/backend/form_engine.py:156).

### AA-06 — Unknown dropdown answers can become real choices

**P1 · Probe + Source · BE field matching**

**Actual:** Matching `Unknown` against Yes/No options returned **no**, because substring matching treats `no` as part of `unknown`. If no match is found, the function ultimately returns the first option. Empty option values can also participate in permissive substring matching.

**Expected:** Unknown stays unresolved; no default choice is treated as a truthful answer.

**Fix:** Use exact normalized matches or explicit validated mappings. Exclude placeholder values. Match numeric ranges mathematically rather than digit substrings. Require user input when the mapping is ambiguous.

**Acceptance:** Unknown/blank/unmatched targets return no selection; Yes and No remain distinct, with tests for placeholders, negation, and ranges.

**Source:** [form_engine.py:167](/D:/WORK/agent-jobs/backend/form_engine.py:167).

### AA-07 — A submit click is recorded as success without confirmation

**P0 · Probe + Source · BE submission/receipts**

**Probe:** A mocked generic page with a submit button, no employer confirmation, and no actual form submission response returned “Application submitted successfully with screenshot receipt saved.” The job was updated to **submitted**. The probe recorded one submit click and zero confirmation-text checks.

Both LinkedIn and generic auto-apply branches click, sleep, capture a screenshot, and construct a success receipt. A screenshot of a validation error would still be a screenshot; it is not proof of acceptance.

**Expected:** Mark Submitted only after a new, credible employer acknowledgement. Otherwise mark Uncertain and prevent automatic retries.

**Fix:** Reuse the standard adapter's confirmation safeguards, including pre-existing-message comparison and explicit unsuccessful/unknown outcomes. Retain a real employer reference or acknowledgement text when available.

**Acceptance:** Validation errors, unchanged forms, timeouts, and missing receipts never become Submitted. A screenshot failure does not change the meaning of a completed submission.

**Sources:** [browser.py:330](/D:/WORK/agent-jobs/backend/browser.py:330), [browser.py:456](/D:/WORK/agent-jobs/backend/browser.py:456).

### AA-08 — A post-click failure can permit a duplicate attempt

**P0 · Probe + Source · BE state machine**

**Probe:** A generic mocked submission clicked once, then raised a synthetic screenshot error. The helper produced no protective state update. Source inspection shows the outer `auto_apply_job` exception handler sets **needs_input** for every caught exception, regardless of whether Submit was clicked.

The worker's fallback for a still-Submitting failure applies only to `kind == 'submit'`, not `auto_apply`.

**Impact:** If an employer accepted the application but a later operation failed, the app may enable another attempt instead of protecting against duplicates.

**Fix:** Track whether submission may have started. All post-click failures must become **uncertain**. Require explicit outcome resolution before retry; use a transactional claim and submission-attempt identity.

**Acceptance:** Failures during click, after click, during screenshot, and during receipt persistence all remain non-retryable until resolved. Pre-click failures can be retried safely.

**Sources:** [browser.py:369](/D:/WORK/agent-jobs/backend/browser.py:369), [worker.py:62](/D:/WORK/agent-jobs/backend/worker.py:62).

### AA-09 — Co-Pilot does not have a durable review session

**P1 · Source · BE browser lifecycle + FE handoff**

**Actual implementation:** LinkedIn Co-Pilot waits only **15 seconds** at the final review point, then returns from `with sync_playwright()`. Generic Co-Pilot returns immediately. There is no dedicated session owner, explicit resume/release control, or durable handoff state tying the open page to the user review.

**Risk:** The UI promises a browser ready for final review, but the driver/session lifetime ends independently of the user. The exact browser-close behavior was not reproduced on a real filled application.

**Fix:** Manage the interactive session independently of a short-lived worker call. Keep it alive until the user completes, cancels, or explicitly closes it. Provide Open session / Resume / Cancel and clear session status.

**Acceptance:** A user can return after several minutes to the intact form and review it without losing state. Closing the session has a defined non-submitted/uncertain outcome.

**Source:** [browser.py:352](/D:/WORK/agent-jobs/backend/browser.py:352).

### AA-10 — Prefill success is reported without a form or upload

**P1 · Probe + Source · BE completion criteria**

**Reproduced:**

- Generic page with no file input and no submit button returned **Application pre-filled. Complete any remaining custom questions and submit.**
- Generic Co-Pilot with a submit button but no file input returned **Application pre-filled with tailored answers and CV**, then set Awaiting review.

The field filler was mocked in these probes to isolate completion logic; upload absence was explicit.

**Expected:** Completion requires verified evidence: correct form, intended fields filled, upload attached, and a reachable review step. Partial work must be reported as partial.

**Fix:** Return structured progress/results with required/completed/unresolved fields, upload status, and stop reason. Do not infer success from reaching the end of a function.

**Acceptance:** No form → unsupported/handoff; missing upload → unresolved upload; rejected fields → validation-needed. Messages describe what actually happened.

**Source:** [browser.py:428](/D:/WORK/agent-jobs/backend/browser.py:428).

### AA-11 — Some exit paths leave the job stuck in Submitting

**P1 · Probe + Source · BE state machine**

**Actual:** The worker sets Submitting before launching the persistent browser. The browser launch happens outside the inner exception handler. If it fails, the `auto_apply` worker has no matching fallback to resolve that state. Similarly, exhausting the LinkedIn loop or reaching a generic page without a submit control returns without a state transition.

**Probe support:** The generic no-submit-button path returned a completion message with **no state updates**. The full browser-launch/12-step-limit cases were source-inspected rather than run live.

**Fix:** Use one explicit terminal-state resolver for every path, including browser startup, no modal, no next button, step limit, and user closure. Distinguish Filling, Waiting for user, Submission attempted, Submitted, and Uncertain.

**Acceptance:** Every completed/failed run leaves a valid actionable job state. No operation remains Submitting unless an actual active or uncertain submission warrants it.

**Sources:** [browser.py:237](/D:/WORK/agent-jobs/backend/browser.py:237), [browser.py:364](/D:/WORK/agent-jobs/backend/browser.py:364), [worker.py:62](/D:/WORK/agent-jobs/backend/worker.py:62).

### AA-12 — File upload is untyped and failures are swallowed

**P1 · Source · BE form adapter**

**Actual:** Both auto-apply paths use the first file input and attach the tailored PDF. They do not establish whether the input is resume, cover letter, portfolio, or another document. Upload exceptions are silently ignored, and the flow can continue to submission.

**Expected:** Upload the correct document only to a positively identified field; verify success and block on unresolved required uploads.

**Fix:** Use field labels/accept constraints and approved document mappings. Verify uploaded filename/state and file integrity. Surface rejection or ambiguity instead of continuing.

**Acceptance:** Resume-not-first, cover-letter-first, multiple files, wrong format, rejected upload, and missing required document are handled correctly without a false “CV attached” message.

**Sources:** [browser.py:313](/D:/WORK/agent-jobs/backend/browser.py:313), [browser.py:441](/D:/WORK/agent-jobs/backend/browser.py:441).

### AA-13 — Agent-generated answers are outside the approved package

**P1 · Source · BE approval model + FE review**

**Actual:** Auto-Apply reads live fields and calls `answer_single_field` during execution, without using `package['answers']` as the authoritative answer set or saving new answers into a reviewable immutable package. The launch request contains mode/headless options rather than a package hash. The worker fetches a package when it runs.

**Impact:** “You approved this exact CV and answer package” does not describe the answers subsequently generated on the employer site. Audit/history cannot reconstruct precisely what was filled.

**Fix:** Persist questions, reviewed answers, source evidence, form fingerprint, target host, and document hashes before submission. Changed/new questions invalidate approval. Return to review rather than generating and sending new answers silently.

**Acceptance:** Every submitted field value is reconstructible from an approved version. Editing profile, CV, answers, form, or target invalidates that approval appropriately.

**Sources:** [app.py:437](/D:/WORK/agent-jobs/backend/app.py:437), [browser.py:372](/D:/WORK/agent-jobs/backend/browser.py:372).

### AA-14 — Prefilled fields and the real phone-country control need typed handling

**P1 · UI + Source · BE field adapter**

**UI:** MBC GROUP's first step has Email address, Phone country code, and Mobile phone number. Email and Egypt (+20) were already selected; the phone textbox was blank.

**Source:** Text fields with a current value longer than one character are skipped without checking against the approved profile. Dropdowns are processed regardless of a correct existing selection. `resolve_contact_field` checks `phone` before `country`, so **Phone country code** resolves to a full phone number, not a country/dial code; the contact-answer path returns that raw value without mapping dropdown options.

**Risk:** Correct saved selections can be mishandled, stale profile values can remain, and selection failures are swallowed. No real values were changed during this audit.

**Fix:** Represent dial code and local number separately. Validate existing answers rather than blindly trusting or overwriting them. Use typed select mappings for contact fields as well as generated answers.

**Acceptance:** Preserve or explicitly reconcile the correct Egypt (+20) choice, fill the right phone format, and surface conflicts with saved LinkedIn data before proceeding.

**Sources:** [form_engine.py:32](/D:/WORK/agent-jobs/backend/form_engine.py:32), [browser.py:372](/D:/WORK/agent-jobs/backend/browser.py:372).

### AA-15 — Auto-Apply omits form validation and challenge safeguards

**P1 · Source · BE browser adapter**

**Actual:** Unlike the standard `submit` path, Auto-Apply does not call the common challenge detector, validate required answers, compare form fingerprints before/after filling, verify resulting field values, check invalid controls, or require a unique submit target. Checkboxes, date inputs, custom comboboxes, and conditional questions are not comprehensively supported. Many exceptions simply continue the loop.

**Impact:** The agent can click Next/Submit with incomplete or incorrect fields, become stuck, or treat an unsupported page as processed.

**Fix:** Share conservative validation primitives across all submission paths. Unsupported controls, CAPTCHA/login challenges, or changed questions must stop with an explicit human handoff. Never bypass challenges.

**Acceptance:** Tests cover invalid required controls, changed forms, CAPTCHA, custom inputs, consent checkboxes, and duplicate/hidden buttons. Each either succeeds with verified values or stops accurately.

**Source:** [browser.py:372](/D:/WORK/agent-jobs/backend/browser.py:372), contrasted with the standard adapter beginning at [line 107](/D:/WORK/agent-jobs/backend/browser.py:107).

### AA-16 — External navigation and agent-session handling are fragile

**P1 · Source · BE navigation + FE session status**

**Actual:** External Apply assumes `expect_popup`; same-tab redirects will time out. Initial selectors rely on `.first` and fixed delays. LinkedIn detection uses substring matching rather than parsed host identity. Auto-Apply does not use the standard adapter's public-URL/request route validation. Login detection uses a narrow selector set, and the session-status endpoint reports whether a profile directory has contents rather than authenticated readiness.

**Scope:** No hostile redirect or wrong-host transmission was attempted. These are implementation gaps, not proven exploitation of the running app.

**Fix:** Support same-tab/popup transitions, validate destination host and transport before uploading/filling, verify account/session readiness, and report profile-lock/challenge/login state separately. Share the same browser session between login setup and handoff with explicit ownership.

**Acceptance:** Same-tab and new-tab employer flows work; unexpected/private destinations stop before data entry; stale login and locked profile errors are actionable.

**Sources:** [browser.py:257](/D:/WORK/agent-jobs/backend/browser.py:257), [browser.py:282](/D:/WORK/agent-jobs/backend/browser.py:282), [app.py:461](/D:/WORK/agent-jobs/backend/app.py:461).

### AA-17 — AI custom answers are requested without supporting CV evidence

**P1 · Source · BE AI prompting/review**

**Actual:** The fallback prompt includes job title/company, the first 600 description characters, candidate name/headline, and the question/options. It does not provide the candidate's verified experience/evidence needed to answer many employer questions truthfully. Exceptions are swallowed, followed by arbitrary option/consent fallbacks.

**Expected:** Answers derive from confirmed evidence and unresolved questions are handed to the user. Provider failure must not change the semantic answer.

**Fix:** Supply only relevant approved evidence, enforce structured supported/unresolved responses, and retain reasons/provenance. Review generated answers before employer entry. Describe every external AI data flow accurately in the UI.

**Acceptance:** Unsupported achievements, salary, experience, and eligibility are never invented; unavailable/malformed provider output results in an unresolved field.

**Source:** [form_engine.py:206](/D:/WORK/agent-jobs/backend/form_engine.py:206).

### AA-18 — The UI presents conflicting application modes

**P2 · UI + Source · FE**

**Observed:** The same Application page says **This site needs a manual application** while offering **AI Auto-Apply Co-Pilot**. Unchecking Co-Pilot changes the button to **Launch Full Auto-Apply**, but adds no dedicated summary of automatic final submission. The panel heading remains Co-Pilot. The checkbox was restored after inspection; Launch was not clicked.

**Cause:** `isAutomated` recognizes only Greenhouse/Lever for one portion of the UI, while Auto-Apply is offered independently.

**Fix:** Expose distinct capabilities—manual, assisted fill, and supported automatic submission—based on actual adapter/preflight results. Use explicit mode names and show the irreversible action/data/package immediately before full-auto launch.

**Acceptance:** The MBC GROUP page accurately explains which agent mode is supported and why. Switching mode clearly communicates whether the agent will press Submit.

**Source:** [JobApplicationPage.tsx:44](/D:/WORK/agent-jobs/frontend/src/pages/jobs/JobApplicationPage.tsx:44).

### AA-19 — Apply detection failure is shown as incomplete job content

**P2 · UI + Source · FE status modeling**

**Observed:** The full responsibilities/required/preferred description is displayed, but the warning reads **Incomplete or brief description: No active application button was found...**. Availability simultaneously says **Verified When Imported**.

**Cause:** The Description page treats any `job.last_error` as a reason to show the incomplete-description warning.

**Fix:** Separate description quality, historical posting verification, browser-session problems, and application-run errors. Preserve error type/run ID and show a relevant recovery action.

**Acceptance:** An Apply failure does not label complete content as incomplete. Historical verification includes a date/context and does not imply current availability was just confirmed.

**Source:** [JobDescriptionPage.tsx:73](/D:/WORK/agent-jobs/frontend/src/pages/jobs/JobDescriptionPage.tsx:73).

### AA-20 — Review checklist completion is conveyed only visually

**P2 · UI + Source · FE accessibility**

**Observed:** The accessibility tree lists **CV reviewed**, **Coverage and gaps reviewed**, and **Current package approved** identically without completion state. Source swaps Circle/CheckCircle icons, both marked `aria-hidden`.

**Expected:** Users can distinguish complete and incomplete prerequisites without relying on icons/color.

**Fix:** Add accessible status text such as “CV review: complete” and explanatory reasons when an action is unavailable. Link unmet prerequisites to their review tabs.

**Acceptance:** Screen-reader output independently identifies each prerequisite's state and how to resolve it.

**Source:** [JobApplicationPage.tsx](/D:/WORK/agent-jobs/frontend/src/pages/jobs/JobApplicationPage.tsx).

### AA-21 — Existing tests give false confidence about application correctness

**P1 · Tests + Source · QA/BE**

**Result:** `tests/test_auto_apply.py` passed all 6 tests. However, it expects location-based salary defaults and hard-coded experience values, and the endpoint test covers only a missing package. It does not reject unreviewed packages or test employer confirmation, uncertainty, upload failures, or Co-Pilot session survival.

**Fix:** Change tests to protect product requirements—truthful answers, explicit approval, exact package binding, reliable receipts—not implementation shortcuts. Add controlled multi-step fixtures and negative-path tests.

**Acceptance:** The defects reproduced below fail the corrected regression suite until fixed. No browser or real employer is needed for guard/answer/state tests; separate controlled end-to-end fixtures validate interaction.

**Source:** [tests/test_auto_apply.py](/D:/WORK/agent-jobs/tests/test_auto_apply.py).

## Isolated probe results

Reproduction utility: [auto_apply_audit_probe.py](/D:/WORK/agent-jobs/reports/auto_apply_audit_probe.py).

Run from `D:\WORK\agent-jobs`:

```powershell
rtk proxy .venv\Scripts\python.exe reports\auto_apply_audit_probe.py
rtk proxy .venv\Scripts\python.exe -m pytest tests/test_auto_apply.py -q
```

The probe program intentionally records current behavior. Successful execution is **not** a correctness pass. It mocks the queue, browser calls, and state updates; its FastAPI lifespan is overridden so it does not initialize the real workspace. Any temporary receipt folder is synthetic. No browser worker callback is dispatched.

| Probe | Observed result |
|---|---|
| Missing legal authorization | Yes |
| Missing sponsorship facts | No |
| Explicitly not authorized | Yes |
| Empty profile, React years | 5 |
| Missing availability facts | Immediately / 2 weeks |
| Cairo annual salary, no preference | UnboundLocalError |
| Berlin annual salary, no preference | UnboundLocalError |
| EGP 65000 monthly preference | 5416 |
| Expected start date | 85000 |
| Unknown dropdown answer | no |
| Agreement fallback without AI | Yes |
| Unreviewed/unapproved full-auto request | HTTP 200; mock queue accepted |
| Submit click with no confirmation | Submitted receipt generated |
| No form/submit target | Prefilled completion message; no state update |
| Co-Pilot with no upload input | Claims CV prefilled; Awaiting review |
| Screenshot error after submit click | Exception after one click; no protective helper state update |

The system Python initially lacked pytest; the repository virtualenv was then used successfully. Test output included Starlette/httpx/AnyIO deprecation warnings; these are maintenance notes, not the cause of the application-flow failures.

## What currently works

- The specified local job and review tabs load.
- The app retains prior failure events and an explicit manual not-submitted outcome.
- Co-Pilot is selected by default and its toggle changes the launch label.
- The real job is reachable and Easy Apply opens a form in the audit browser.
- The standard submission adapter already contains useful approval/file/form/confirmation checks that can be shared with Auto-Apply.
- The API rejects a completely missing package, and busy/submitted/uncertain checks exist. Those checks do not replace missing approval and outcome enforcement.

## Recommended implementation order

1. **Block unattended Full Auto-Apply until AA-02, AA-03, AA-07, and AA-08 are fixed.** Keep explicit user review and a truthful manual path available.
2. Build one shared submission contract: immutable approved package, verified answers/documents, transactional attempt identity, and conservative receipt/uncertainty handling.
3. Replace guessed answers with evidence-backed answers or unresolved questions. Correct salary parsing, dropdown mapping, and phone field typing.
4. Add a durable browser-session manager and explicit Co-Pilot handoff. Resolve login/session readiness before scanning the posting.
5. Reproduce the MBC GROUP detection failure in the app's exact persistent session and capture the diagnostic evidence needed to fix it.
6. Verify upload targets, field values, validation, multi-step navigation, and conditional questions before any submit action.
7. Align UI modes, checklist states, operation errors, and live progress with the backend state machine.
8. Add controlled end-to-end fixtures and regression tests for the matrix below, then retest the live posting only to the user-reviewed boundary.

## Remaining test matrix before release

| Area | Required scenarios |
|---|---|
| Browser/session | Fresh profile, expired login, account mismatch, locked profile, browser launch failure, user closes browser, app restart |
| Posting discovery | Active Easy Apply, external Apply, same-tab redirect, popup, delayed rendering, hidden duplicate button, closed job, wrong-host redirect |
| Forms | Multi-step navigation, dynamic questions, custom selects, radios with opposing answers, consent checkboxes, date/number validation, iframe forms |
| Answers | Missing/contradictory eligibility, unknown skills, salary currency/period/ranges, evidence-supported experience, provider failure, malicious page instructions |
| Uploads | Resume not first, cover letter required, absent input, rejected size/type, upload timeout, wrong/stale document hash |
| Approval | Unreviewed CV, unreviewed coverage, dirty draft, stale package hash, changed form, changed profile, generated new answers |
| Co-Pilot | Review after 5+ minutes, resume/cancel, manual submit observed, browser closure without submit, no automatic final click |
| Submit/outcomes | Accepted receipt, rejected validation, unchanged page, pre-existing success text, click timeout, screenshot failure, persistence failure, network loss |
| Duplicate prevention | Double-click, concurrent requests, restart after click, uncertain outcome, already-submitted job |
| UX/accessibility | Accurate mode labels, unmet prerequisite reasons, keyboard operation, live run status, contextual error recovery |

## Final state and limitations

The local Application tab was retained for inspection with **Co-Pilot checked**. No new live Auto-Apply run was started. The external first-step form was inspected only; no new contact values were typed, no Next button was pressed, and no application was submitted. Opening Easy Apply may have initialized an employer-side draft; its persistence was not investigated or modified.

Source findings refer to the local checkout read during this audit. Browser observations establish the visible behavior of the running app; a build/revision identity match was not independently verified. The historical failed runs, remaining LinkedIn form pages, and real agent session lifecycle were not re-executed. Consequently this report is a targeted flow audit with isolated failure reproduction, not an end-to-end real submission certification.
