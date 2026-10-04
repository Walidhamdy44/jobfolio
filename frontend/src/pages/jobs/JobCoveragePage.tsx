import { Link, useOutletContext } from 'react-router-dom'
import { Check, CircleHelp, Circle, ChevronRight, Sparkles, ArrowRight } from 'lucide-react'
import { useReviewDraft } from '../../features/review/ReviewDraftContext'
import { Button } from '../../shared/ui/Button'
import { Notice } from '../../shared/ui/Notice'
import { Empty } from '../../shared/ui/Empty'
import type { Job, Package } from '../../types'

export function JobCoveragePage() {
  const { job, pkg, isLocked, setToast, bootstrap } = useOutletContext<{
    job: Job
    pkg: Package | null
    isLocked: boolean
    setToast: (msg: string) => void
    bootstrap?: { connections?: { connected?: boolean } }
  }>()

  const {
    coverageChecked,
    setCoverageChecked,
    supports,
    setSupportIndex,
    isDirty,
    isConflicted,
    saveReview,
    resetToPackage,
    isSaving,
    saveError,
  } = useReviewDraft()

  if (!pkg) {
    return (
      <Empty icon="cv" title="No requirements audit yet">
        Prepare a CV for this job first to calculate evidence coverage and audit qualifications.
      </Empty>
    )
  }

  const missingCount = pkg.requirements.filter((requirement) => requirement.support === 'missing').length

  const handleSaveReview = async () => {
    try {
      await saveReview()
      setToast('Coverage review saved.')
    } catch (e) {
      setToast((e as Error).message)
    }
  }

  return (
    <>
      <div className="coverage-header">
        <div>
          <h2>See the evidence behind the fit.</h2>
          <p>{pkg.note} This is not an employer ATS score.</p>
        </div>
        <div className="coverage-value">
          <strong>
            {pkg.score}
            <span>%</span>
          </strong>
          <small>{pkg.coverage_reviewed ? 'Reviewed coverage' : 'Provisional coverage'}</small>
        </div>
      </div>

      <div className="coverage-legend" role="note" aria-label="Support level legend">
        <span>
          <i className="full" aria-hidden="true" />
          Fully supported
        </span>
        <span>
          <i className="partial" aria-hidden="true" />
          Partially supported
        </span>
        <span>
          <i className="missing" aria-hidden="true" />
          Not supported
        </span>
        <span>Weighting: Required (3×) · Preferred (1×)</span>
      </div>

      {missingCount > 0 && (
        <section className="coverage-improve-launch" aria-labelledby="coverage-improve-title">
          <div className="coverage-improve-copy">
            <Sparkles size={18} aria-hidden="true" />
            <div>
              <h3 id="coverage-improve-title">Work through {missingCount} missing requirements</h3>
              <p>
                Review the final CV beside its gaps. AI can suggest evidence-backed wording; you choose what to include.
              </p>
              {!bootstrap?.connections?.connected && (
                <small>Connect an AI provider before drafting changes.</small>
              )}
            </div>
          </div>
          <Link
            to={`/jobs/${job.id}/coverage/improve`}
            className={`button primary${isLocked ? ' disabled-link' : ''}`}
            aria-disabled={isLocked}
            onClick={(event) => { if (isLocked) event.preventDefault() }}
          >
            Review missing requirements
            <ArrowRight size={15} />
          </Link>
        </section>
      )}

      {isConflicted && (
        <Notice kind="warning">
          A new package version was generated while you had unsaved edits. Review requirements or{' '}
          <button
            type="button"
            className="text-button"
            onClick={resetToPackage}
            style={{ display: 'inline', padding: 0 }}
          >
            reload latest server package
          </button>
          .
        </Notice>
      )}

      {saveError && <Notice kind="error">{saveError}</Notice>}

      <div className="requirements" role="list">
        {pkg.requirements.map((r, i) => {
          const currentSupport = supports[i] || r.support
          return (
            <div className="requirement" key={i} role="listitem">
              <div className="requirement-top">
                <span className={`support-icon ${currentSupport}`} aria-hidden="true">
                  {currentSupport === 'full' ? (
                    <Check size={17} />
                  ) : currentSupport === 'partial' ? (
                    <CircleHelp size={17} />
                  ) : (
                    <Circle size={17} />
                  )}
                </span>
                <div>
                  <h3>{r.text}</h3>
                  <small>
                    {r.priority === 'required' ? 'Required' : 'Preferred'} · weight {r.weight}
                  </small>
                </div>
                <select
                  aria-label={`Support rating for: ${r.text}`}
                  value={currentSupport}
                  disabled={isLocked || isSaving}
                  onChange={(e) =>
                    setSupportIndex(i, e.target.value as 'full' | 'partial' | 'missing')
                  }
                >
                  <option value="full" disabled={!r.evidence_ids.length}>
                    Full support
                  </option>
                  <option value="partial" disabled={!r.evidence_ids.length}>
                    Partial support
                  </option>
                  <option value="missing">Missing</option>
                </select>
              </div>

              <p className="requirement-explanation">{r.explanation}</p>

              <details>
                <summary>
                  View requirement quote and CV evidence
                  <ChevronRight size={14} />
                </summary>
                <div className="evidence-detail">
                  <div>
                    <h4>Job description</h4>
                    <blockquote>{r.source_quote}</blockquote>
                  </div>
                  <div>
                    <h4>Your CV</h4>
                    {r.evidence.length ? (
                      r.evidence.map((e) => <blockquote key={e.id}>{e.text}</blockquote>)
                    ) : (
                      <p>
                        No supporting passage was identified in your master profile. Add confirmed
                        experience to your master profile and prepare again if this is incomplete.
                      </p>
                    )}
                  </div>
                </div>
              </details>
            </div>
          )
        })}
      </div>

      <div className="review-bottom">
        <label className="check-field">
          <input
            type="checkbox"
            checked={coverageChecked}
            disabled={isLocked || isSaving}
            onChange={(e) => setCoverageChecked(e.target.checked)}
          />
          <span>I reviewed every requirement, its evidence, and any missing qualifications.</span>
        </label>

        <Button
          kind="primary"
          disabled={isLocked || !isDirty || isSaving}
          loading={isSaving}
          onClick={() => void handleSaveReview()}
        >
          Save coverage review
          <Check size={15} />
        </Button>
      </div>
    </>
  )
}
