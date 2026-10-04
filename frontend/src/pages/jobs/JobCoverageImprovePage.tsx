import { useMemo, useState } from 'react'
import { Link, useNavigate, useOutletContext } from 'react-router-dom'
import { ArrowLeft, ArrowRight, Check, ChevronDown, CircleHelp, FileText, Search, Sparkles } from 'lucide-react'
import {
  useApplyCoverageImprovementsMutation,
  useDraftCoverageImprovementsMutation,
} from '../../features/jobs/queries'
import { useReviewDraft } from '../../features/review/ReviewDraftContext'
import { CVPreview } from '../../features/documents/components/CVPreview'
import { Button } from '../../shared/ui/Button'
import { Empty } from '../../shared/ui/Empty'
import { Notice } from '../../shared/ui/Notice'
import type { Bootstrap, CVImprovementDraft, CVImprovementSuggestion, Job, Package, Profile } from '../../types'

type EvidenceDraft = { text: string; confirmed: boolean }

export function JobCoverageImprovePage() {
  const { job, pkg, isLocked, setToast, bootstrap } = useOutletContext<{
    job: Job
    pkg: Package | null
    isLocked: boolean
    setToast: (message: string) => void
    bootstrap?: Bootstrap
  }>()
  const navigate = useNavigate()
  const draftMutation = useDraftCoverageImprovementsMutation(job.id)
  const applyMutation = useApplyCoverageImprovementsMutation(job.id)
  const {
    isDirty: reviewIsDirty,
    isConflicted: reviewIsConflicted,
    resetToPackage,
  } = useReviewDraft()
  const [search, setSearch] = useState('')
  const [priority, setPriority] = useState<'all' | 'required' | 'preferred'>('all')
  const [selectedIndexes, setSelectedIndexes] = useState<number[]>([])
  const [evidenceDrafts, setEvidenceDrafts] = useState<Record<number, EvidenceDraft>>({})
  const [draft, setDraft] = useState<CVImprovementDraft | null>(null)
  const [acceptedIds, setAcceptedIds] = useState<string[]>([])
  const [actionError, setActionError] = useState('')

  const profileEntryIds = useMemo(() => new Set(
    pkg?.profile.sections.flatMap((section) => section.items.map((item) => item.id)) || []
  ), [pkg])
  const missing = useMemo(() => pkg?.requirements
    .map((requirement, requirementIndex) => ({ requirement, requirementIndex }))
    .filter(({ requirement }) => requirement.support === 'missing') || [], [pkg])
  const visibleMissing = missing.filter(({ requirement }) => {
    const matchesQuery = !search.trim() || requirement.text.toLowerCase().includes(search.trim().toLowerCase())
    const matchesPriority = priority === 'all' || requirement.priority === priority
    return matchesQuery && matchesPriority
  })
  const selectedRows = missing.filter(({ requirementIndex }) => selectedIndexes.includes(requirementIndex))
  const visibleAreSelected = visibleMissing.length > 0 && visibleMissing.every(({ requirementIndex }) => selectedIndexes.includes(requirementIndex))
  const suggestions = draft?.suggestions || []
  const accepted = suggestions.filter((suggestion) => acceptedIds.includes(suggestion.id))
  const isAiConnected = Boolean(bootstrap?.connections?.connected)
  const isProfileStale = Boolean(bootstrap?.profile && pkg && pkg.profile_revision !== bootstrap.profile.revision)
  const hasUncommittedReview = reviewIsDirty || reviewIsConflicted
  const isApplying = applyMutation.isPending
  const isDrafting = draftMutation.isPending

  const candidateProfile = useMemo(() => {
    if (!pkg) return null
    const profile = JSON.parse(JSON.stringify(pkg.profile)) as Profile
    for (const suggestion of accepted) {
      if (suggestion.action === 'rewrite') {
        const item = profile.sections.flatMap((section) => section.items)
          .find((entry) => entry.id === suggestion.evidence_id)
        if (item) item.text = suggestion.after
      } else {
        let summary = profile.sections.find((section) => section.title === 'Summary')
        if (!summary) {
          summary = { title: 'Summary', items: [] }
          profile.sections.unshift(summary)
        }
        summary.items.push({ id: `draft-${suggestion.id}`, text: suggestion.after })
      }
    }
    return profile
  }, [accepted, pkg])

  const highlightedIds = accepted.map((suggestion) =>
    suggestion.action === 'rewrite' ? suggestion.evidence_id : `draft-${suggestion.id}`
  )

  if (!pkg) {
    return (
      <Empty icon="cv" title="Prepare a CV before improving coverage">
        This workspace uses the final job-specific CV and its verified requirement evidence.
      </Empty>
    )
  }

  if (!missing.length) {
    return (
      <div className="cv-improver-page">
        <Link to={`/jobs/${job.id}/coverage`} className="text-button back-button">
          <ArrowLeft size={15} /> Back to requirement coverage
        </Link>
        <Empty icon="cv" title="No missing requirements to improve">
          Every extracted requirement has at least some CV evidence. You can continue reviewing coverage or inspect the final CV.
        </Empty>
      </div>
    )
  }

  const hasSourceEvidence = (requirement: Package['requirements'][number]) =>
    requirement.evidence_ids.some((id) => profileEntryIds.has(id))

  const clearDraft = () => {
    setDraft(null)
    setAcceptedIds([])
    setActionError('')
  }

  const toggleRequirement = (index: number) => {
    setSelectedIndexes((current) => current.includes(index)
      ? current.filter((item) => item !== index)
      : [...current, index])
    clearDraft()
  }

  const toggleVisible = () => {
    const visibleIds = visibleMissing.map(({ requirementIndex }) => requirementIndex)
    setSelectedIndexes((current) => visibleAreSelected
      ? current.filter((index) => !visibleIds.includes(index))
      : [...new Set([...current, ...visibleIds])])
    clearDraft()
  }

  const updateEvidence = (index: number, changes: Partial<EvidenceDraft>) => {
    setEvidenceDrafts((current) => ({
      ...current,
      [index]: { ...(current[index] || { text: '', confirmed: false }), ...changes },
    }))
    clearDraft()
  }

  const readyToDraft = !hasUncommittedReview && !isProfileStale && selectedRows.length > 0 && selectedRows.every(({ requirement, requirementIndex }) => {
    if (hasSourceEvidence(requirement)) return true
    const evidence = evidenceDrafts[requirementIndex]
    return Boolean(evidence?.text.trim().length >= 12 && evidence.confirmed)
  })

  const handleDraft = async () => {
    if (!pkg || !readyToDraft || hasUncommittedReview || isProfileStale) return
    setActionError('')
    try {
      const result = await draftMutation.mutateAsync({
        package_hash: pkg.hash,
        selections: selectedRows.map(({ requirementIndex }) => ({
          requirement_index: requirementIndex,
          evidence_text: evidenceDrafts[requirementIndex]?.text.trim() || '',
          evidence_confirmed: evidenceDrafts[requirementIndex]?.confirmed || false,
        })),
      })
      setDraft(result)
      setAcceptedIds([])
    } catch (error) {
      setActionError((error as Error).message || 'Could not draft CV improvements. Try again or update your master CV.')
    }
  }

  const handleApply = async () => {
    if (!pkg || !draft || acceptedIds.length === 0) return
    setActionError('')
    resetToPackage()
    try {
      const result = await applyMutation.mutateAsync({
        package_hash: pkg.hash,
        draft_id: draft.draft_id,
        suggestion_ids: acceptedIds,
      })
      setToast(`Applied ${result.change_count} AI-audited edit${result.change_count === 1 ? '' : 's'}. Review the new CV before approval.`)
      navigate(`/jobs/${job.id}/cv`)
    } catch (error) {
      setDraft(null)
      setAcceptedIds([])
      setActionError((error as Error).message || 'Could not apply the selected changes. Reload the package and draft again.')
    }
  }

  const toggleSuggestion = (id: string) => {
    setAcceptedIds((current) => current.includes(id)
      ? current.filter((item) => item !== id)
      : [...current, id])
  }

  const selectAllSuggestions = () => setAcceptedIds(suggestions.map((suggestion) => suggestion.id))
  const clearSuggestions = () => setAcceptedIds([])

  return (
    <div className="cv-improver-page">
      <Link to={`/jobs/${job.id}/coverage`} className="text-button back-button">
        <ArrowLeft size={15} /> Back to requirement coverage
      </Link>

      <header className="cv-improver-heading">
        <div>
          <div className="cv-improver-title-line">
            <h2>Improve this CV against the missing requirements</h2>
            <span className="improve-count">{missing.length} fully missing</span>
          </div>
          <p>Select the gaps to work on. AI will look for a truthful place in the current CV, then you decide which audited edits to apply.</p>
        </div>
      </header>

      {isLocked && (
        <Notice kind="warning">This application is submitted or uncertain, so its CV package cannot be changed.</Notice>
      )}
      {!isAiConnected && !isLocked && (
        <Notice kind="warning">
          Connect an AI provider in <Link to="/settings/ai">Connections</Link> to draft evidence-checked CV improvements.
        </Notice>
      )}
      {hasUncommittedReview && (
        <Notice kind="warning">
          Save or discard your unsaved CV or coverage review changes first.{' '}
          <Link to={`/jobs/${job.id}/coverage`}>Return to coverage review</Link>.
        </Notice>
      )}
      {isProfileStale && (
        <Notice kind="warning">
          Your master profile changed after this CV was prepared. Prepare a fresh CV from the job page before improving coverage.
        </Notice>
      )}
      {actionError && <Notice kind="error">{actionError}</Notice>}
      {draftMutation.isPending && (
        <Notice>
          AI is reviewing the selected requirements against your CV evidence. This can take a little while; no CV files change until you apply edits.
        </Notice>
      )}
      {applyMutation.isPending && (
        <Notice>
          Building and verifying a new CV package. Your current package remains available until the new files are ready.
        </Notice>
      )}

      <div className="cv-improver-grid">
        <section className="cv-improver-workflow" aria-labelledby="missing-list-title">
          <div className="improve-list-heading">
            <div>
              <h3 id="missing-list-title">Missing requirements</h3>
              <p>{selectedIndexes.length} selected of {missing.length}</p>
            </div>
            <Button disabled={isLocked || isProfileStale || hasUncommittedReview || isApplying || isDrafting || !visibleMissing.length} onClick={toggleVisible}>
              {visibleAreSelected ? 'Clear visible' : 'Select visible'}
            </Button>
          </div>

          <div className="improve-filters">
            <label className="improve-search">
              <Search size={15} aria-hidden="true" />
              <span className="sr-only">Search missing requirements</span>
              <input
                value={search}
                onChange={(event) => setSearch(event.target.value)}
                placeholder="Find a requirement"
              />
            </label>
            <label className="improve-priority-filter">
              <span className="sr-only">Filter by priority</span>
              <select value={priority} onChange={(event) => setPriority(event.target.value as typeof priority)}>
                <option value="all">All priorities</option>
                <option value="required">Required</option>
                <option value="preferred">Preferred</option>
              </select>
            </label>
          </div>

          <div className="improve-requirements" role="list" aria-label="Missing job requirements">
            {visibleMissing.map(({ requirement, requirementIndex }) => {
              const checked = selectedIndexes.includes(requirementIndex)
              const hasEvidence = hasSourceEvidence(requirement)
              const evidence = evidenceDrafts[requirementIndex] || { text: '', confirmed: false }
              return (
                <article className={`improve-requirement${checked ? ' selected' : ''}`} key={requirementIndex} role="listitem">
                  <div className="improve-requirement-main">
                    <label className="improve-requirement-check">
                      <input
                        type="checkbox"
                        checked={checked}
                        disabled={isLocked || isProfileStale || hasUncommittedReview || isApplying || isDrafting}
                        onChange={() => toggleRequirement(requirementIndex)}
                        aria-label={`Select ${requirement.text}`}
                      />
                    </label>
                    <div className="improve-requirement-copy">
                      <div className="improve-requirement-title">
                        <h4>{requirement.text}</h4>
                        <span className={`improve-priority ${requirement.priority}`}>
                          {requirement.priority === 'required' ? 'Required' : 'Preferred'}
                        </span>
                      </div>
                      <p>{requirement.explanation}</p>
                      <details className="improve-requirement-detail">
                        <summary>
                          Job quote and current CV evidence <ChevronDown size={14} aria-hidden="true" />
                        </summary>
                        <div className="improve-evidence-columns">
                          <div>
                            <small>From the job posting</small>
                            <blockquote>{requirement.source_quote}</blockquote>
                          </div>
                          <div>
                            <small>From this CV</small>
                            {requirement.evidence.length ? requirement.evidence.map((item) => (
                              <blockquote key={item.id}>{item.text}</blockquote>
                            )) : <p>No source statement was matched to this requirement.</p>}
                          </div>
                        </div>
                      </details>
                      {!hasEvidence && <span className="improve-no-evidence"><CircleHelp size={13} /> Needs your evidence</span>}
                    </div>
                  </div>

                  {checked && !hasEvidence && (
                    <div className="improve-user-evidence">
                      <label htmlFor={`user-evidence-${requirementIndex}`}>What experience or qualification supports this?</label>
                      <textarea
                        id={`user-evidence-${requirementIndex}`}
                        value={evidence.text}
                        maxLength={2000}
                        rows={3}
                        disabled={isProfileStale || hasUncommittedReview || isApplying || isDrafting}
                        onChange={(event) => updateEvidence(requirementIndex, { text: event.target.value })}
                        placeholder="Describe what you actually did or hold. AI will not add facts beyond this evidence."
                      />
                      <label className="improve-confirm-evidence">
                        <input
                          type="checkbox"
                          checked={evidence.confirmed}
                          disabled={isProfileStale || hasUncommittedReview || isApplying || isDrafting || evidence.text.trim().length < 12}
                          onChange={(event) => updateEvidence(requirementIndex, { confirmed: event.target.checked })}
                        />
                        <span>I confirm this is accurate experience or a qualification I have.</span>
                      </label>
                    </div>
                  )}
                </article>
              )
            })}
            {!visibleMissing.length && (
              <p className="improve-filter-empty">No missing requirements match this search.</p>
            )}
          </div>

          <div className="improve-draft-actions">
            <div>
              <strong>{selectedIndexes.length ? `${selectedIndexes.length} requirement${selectedIndexes.length === 1 ? '' : 's'} ready for review` : 'Choose the gaps you want to address'}</strong>
              <small>New facts need evidence and your confirmation. Existing CV text is checked against its original source.</small>
            </div>
            <Button
              kind="primary"
              disabled={!readyToDraft || !isAiConnected || isLocked || isDrafting || isApplying}
              loading={isDrafting}
              onClick={() => void handleDraft()}
            >
              <Sparkles size={15} /> Draft selected edits
            </Button>
          </div>

          {draft && (
            <section className="improve-suggestions" aria-labelledby="suggestions-title">
              <div className="improve-suggestions-heading">
                <div>
                  <h3 id="suggestions-title">AI-audited suggestions <span>{suggestions.length}</span></h3>
                  <p>Nothing changes until you select and apply an edit.</p>
                </div>
                {suggestions.length > 0 && (
                  <div className="improve-bulk-actions">
                    <button type="button" onClick={selectAllSuggestions}>Select all</button>
                    <button type="button" onClick={clearSuggestions}>Clear</button>
                  </div>
                )}
              </div>

              {suggestions.map((suggestion) => (
                <SuggestionReview
                  key={suggestion.id}
                  suggestion={suggestion}
                  requirements={pkg.requirements}
                  checked={acceptedIds.includes(suggestion.id)}
                  disabled={isLocked || isDrafting || isApplying}
                  onToggle={() => toggleSuggestion(suggestion.id)}
                />
              ))}

              {draft.unresolved.length > 0 && (
                <div className="improve-unresolved" role="status">
                  <strong>{draft.unresolved.length} gap{draft.unresolved.length === 1 ? '' : 's'} did not pass the evidence check</strong>
                  <p>AI left these unchanged. Add more accurate experience to your master CV, or provide clearer evidence above and draft again.</p>
                  <ul>
                    {draft.unresolved.map((item) => <li key={item.requirement_index}>{item.text}</li>)}
                  </ul>
                </div>
              )}
              {suggestions.length === 0 && draft.unresolved.length === 0 && (
                <p className="improve-filter-empty">No safe edits were found. Add clearer evidence or update your master CV, then try again.</p>
              )}
            </section>
          )}
        </section>

        <aside className="cv-improver-preview" aria-labelledby="final-cv-title">
          <header>
            <div>
              <h3 id="final-cv-title">Final CV preview</h3>
              <p>{accepted.length ? `${accepted.length} selected edit${accepted.length === 1 ? '' : 's'} shown` : 'Your current job-specific CV'}</p>
            </div>
            {accepted.length > 0 && <span className="proposed-legend"><i aria-hidden="true" /> Proposed</span>}
          </header>
          {candidateProfile && <CVPreview profile={candidateProfile} highlightedIds={highlightedIds} />}
        </aside>
      </div>

      <footer className="improve-apply-bar">
        <div>
          <FileText size={17} aria-hidden="true" />
          <p>
            <strong>{accepted.length ? `${accepted.length} audited edit${accepted.length === 1 ? '' : 's'} selected` : 'The master CV stays untouched'}</strong>
            <span>Applying creates a new package and sends you to the normal CV review. Approval resets until you review it again.</span>
          </p>
        </div>
        <Button
          kind="primary"
          disabled={!draft || accepted.length === 0 || isLocked || isProfileStale || hasUncommittedReview || isApplying || isDrafting}
          loading={isApplying}
          onClick={() => void handleApply()}
        >
          Apply selected edits
          <ArrowRight size={15} />
        </Button>
      </footer>
    </div>
  )
}

function SuggestionReview({
  suggestion,
  requirements,
  checked,
  disabled,
  onToggle,
}: {
  suggestion: CVImprovementSuggestion
  requirements: Package['requirements']
  checked: boolean
  disabled: boolean
  onToggle: () => void
}) {
  const addressed = suggestion.requirement_indices
    .map((index) => requirements[index]?.text)
    .filter((text): text is string => Boolean(text))
  return (
    <article className={`improve-suggestion${checked ? ' selected' : ''}`}>
      <div className="improve-suggestion-top">
        <label>
          <input type="checkbox" checked={checked} disabled={disabled} onChange={onToggle} />
          <span>{checked ? 'Selected' : 'Include edit'}</span>
        </label>
        <span className="improve-placement">{suggestion.action === 'add' ? 'Add to Summary' : `Update ${suggestion.section}`}</span>
      </div>
      <div className="improve-addressed">
        {addressed.map((text) => <span key={text}>{text}</span>)}
      </div>
      <div className="improve-diff">
        <div>
          <small>{suggestion.action === 'add' ? 'New CV statement' : 'Current wording'}</small>
          <p>{suggestion.before || 'No existing statement'}</p>
        </div>
        <ArrowRight size={15} aria-hidden="true" />
        <div>
          <small>AI proposal</small>
          <p>{suggestion.after}</p>
        </div>
      </div>
      <details className="improve-source-detail">
        <summary>Evidence used <ChevronDown size={13} aria-hidden="true" /></summary>
        <blockquote>{suggestion.source_evidence}</blockquote>
      </details>
      <span className="improve-audit-status"><Check size={13} aria-hidden="true" /> Passed source-evidence audit</span>
    </article>
  )
}
