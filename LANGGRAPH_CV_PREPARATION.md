# LangGraph AI CV preparation

## Overview

AI CV tailoring runs as a resumable LangGraph workflow. Local CV preparation remains in the existing synchronous Python flow. A completed AI workflow publishes the same review package consumed by the current CV, coverage, and application screens. The graph never approves a package or submits an application.

## Workflow

1. **Load snapshot** — load the job and master profile, reject locked application states, and save a fingerprint of the inputs and the profile revision.
2. **Extract requirements** — ask the configured provider for structured candidate requirements and source quotes through `providers.ask()`.
3. **Verify requirements** — check each quote against the job description, merge recognizable criteria omitted by the model, deduplicate, and keep the current local requirement safeguards.
4. **Draft CV edits** — send only eligible CV prose and requirements to the provider. Numeric changes and edits to protected fields are filtered out.
5. **Audit edits** — ask the provider to verify each proposed change against its original evidence. Only supported changes are applied to a copy of the master profile.
6. **Assess coverage** — score every requirement against the finished CV. If AI coverage assessment fails, preserve the existing conservative local fallback.
7. **Publish package** — generate PDF and Word files, verify their hashes, and save a review-ready package. The prior package remains available until the new exports are generated.

## Graph state and persistence

The typed graph state holds the job/profile snapshots, source fingerprint and profile revision, raw and verified requirements, editable source entries, proposed rewrites, audited profile changes, coverage rows, score, and package/run IDs. Provider credentials and callback functions are not part of the graph state.

Checkpoints live in `data/prepare-checkpoints.sqlite3`, beside the app's existing local data. The graph thread ID, worker run ID, package ID, and generated document directory use the same unique run ID. Checkpoint writes use synchronous durability at graph-step boundaries. Strict MessagePack deserialization is enabled, and external tracing is not configured. The local SQLite checkpoint package is intended for local and lightweight deployments ([package details](https://pypi.org/project/langgraph-checkpoint-sqlite/)).

When the app restarts, the existing store marks queued/running jobs interrupted. A resume candidate is shown only when the latest preparation run for the job is interrupted, its graph checkpoint has pending work, and the saved job/profile fingerprint still matches the current inputs. The provider connection is checked again before queueing resume. If the job or profile changed, start a fresh preparation.

Resumption uses the same graph thread ID and starts at the checkpointed node boundary. The current node can run again after a crash, so publishing checks for an existing package with that run ID and verifies its files before reusing it. Published, failed, and superseded checkpoint threads are removed. Interrupted work stays checkpointed until it is resumed or a newer preparation supersedes it.

## API and UI behavior

- `POST /api/jobs/{job_id}/prepare` keeps its existing request and `{run_id}` response. `mode: "ai"` uses LangGraph; local mode uses the existing path.
- `GET /api/jobs/{job_id}` includes `resumable_prepare_run`, either the latest eligible interrupted AI run or `null`.
- `POST /api/jobs/{job_id}/prepare/{run_id}/resume` queues that same run ID and returns `{run_id}`. The worker atomically rejects duplicate or non-interrupted resumes.
- The job page shows **Resume preparation** when the API reports an eligible run. When an AI run started from the current job page completes, the page refreshes job detail and opens the CV tab if the user is still on that job. Leaving the job page cancels the automatic navigation.

The current user review, evidence checks, profile revision check, package hash, explicit approval, and separate submission endpoint remain authoritative.

## Improving missing coverage after preparation

The coverage screen can open a separate CV improvement workspace for requirements currently marked `missing`. This interactive feature is not another LangGraph preparation run: it drafts only after the user selects gaps, inspects the final job-specific CV beside the proposed edits, and chooses which evidence-audited edits to apply.

- `POST /api/jobs/{job_id}/coverage/improvements/draft` checks the current package hash and selected missing requirement indexes. If a selected gap has no CV evidence, the user must provide and confirm truthful experience before the AI can draft a new statement. Existing-source rewrites and new statements are audited against their original or user-confirmed evidence; unsupported suggestions are omitted.
- `POST /api/jobs/{job_id}/coverage/improvements/apply` accepts a local, single-use draft ID plus the chosen suggestion IDs. Drafts are package-hash-bound, kept in the local SQLite database for up to seven days, and superseded by a newer draft. Concurrent apply operations for one job are rejected; a draft left applying by a crash is made unusable on restart, so the user can draft again.
- Applying creates a new package and fresh PDF/DOCX exports without modifying the master CV or replacing the previous package. Requirement coverage is reassessed, review and approval flags reset, and the user returns to the standard CV review screen. Approval remains bound to the new package hash.
- A new bullet based on user-supplied experience is placed in the package’s Summary and its source text is retained with the package for review. User-provided evidence remains job-specific; it is not silently written into the master profile.

## Failure handling and privacy

An invalid or unsupported source quote fails before edits are applied. Unsupported edits are discarded. A failed coverage call uses the existing local assessment. Export or database failures do not replace the prior package; a partially generated per-run directory can be overwritten when the publish node resumes before a package row exists. Once a package row exists, its verified files are reused rather than overwritten.

The graph checkpoint contains personal profile and job-description data. It remains local under the ignored `data/` directory. LangSmith or other external tracing must not be enabled implicitly. Checkpoint cleanup follows the run lifecycle described above.

## Acceptance checks

- AI preparation executes the seven graph stages in order and yields a package with valid PDF/Word hashes.
- Requirement quotes are verified, omitted explicit checklist items are merged, unsupported rewrites are rejected, and failed coverage falls back conservatively.
- Failure before publish leaves the previous package unchanged.
- Restarting an interrupted graph exposes Resume only for its latest valid run. Resuming reuses completed graph stages and produces one package for the same run ID.
- Resume is rejected for changed job/profile inputs, missing checkpoints, superseded runs, or concurrent work. A fresh local preparation keeps its existing behavior.
- Completion from the current job page opens its CV tab after refreshing detail; completion after leaving that job does not navigate the user back.

## Manual walkthrough

1. Connect an AI provider, open a job, and start **Tailor with AI**.
2. Confirm progress messages appear and successful completion opens the CV tab with the new package.
3. Interrupt the app during preparation and restart it. Confirm **Resume preparation** appears for that job.
4. Resume and confirm the same run completes without creating a duplicate package.
5. Change the master profile or job description while a run is interrupted; confirm the old run is no longer resumable and a fresh run is required.
6. Prepare a CV locally and confirm the existing local workflow and review screens still work.
