import { useOutletContext } from 'react-router-dom'
import { Download, ChevronRight, Check } from 'lucide-react'
import { CVPreview } from '../../features/documents/components/CVPreview'
import { useReviewDraft } from '../../features/review/ReviewDraftContext'
import { Button } from '../../shared/ui/Button'
import { Notice } from '../../shared/ui/Notice'
import { Empty } from '../../shared/ui/Empty'
import type { Job, Package } from '../../types'

export function JobCvPage() {
  const { job, pkg, isLocked, setToast } = useOutletContext<{
    job: Job
    pkg: Package | null
    isLocked: boolean
    setToast: (msg: string) => void
  }>()

  const {
    cvChecked,
    setCVChecked,
    isDirty,
    isConflicted,
    saveReview,
    resetToPackage,
    isSaving,
    saveError,
  } = useReviewDraft()

  if (!pkg) {
    return (
      <Empty icon="cv" title="Start with your tailored CV">
        Prepare a local CV or use AI tailoring to create a review package for this job.
      </Empty>
    )
  }

  const handleSaveReview = async () => {
    try {
      await saveReview()
      setToast('Review saved. Approval applies only to this exact package version.')
    } catch (e) {
      setToast((e as Error).message)
    }
  }

  return (
    <>
      <div className="section-title">
        <div>
          <h2>A CV with this role in mind</h2>
          <p className="muted">
            {pkg.mode === 'ai'
              ? 'AI rewrites checked against source evidence.'
              : 'Local version: original wording, relevant skill groups first.'}
          </p>
        </div>
        <div className="button-group">
          <a
            className="button"
            href={`/api/jobs/${job.id}/documents/pdf`}
            download
          >
            <Download size={15} />
            PDF
          </a>
          <a
            className="button"
            href={`/api/jobs/${job.id}/documents/docx`}
            download
          >
            Word
          </a>
        </div>
      </div>

      {isConflicted && (
        <Notice kind="warning">
          A new package version was generated while you had unsaved edits. Review the changes below or{' '}
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

      <div className="cv-review-layout">
        <CVPreview profile={pkg.profile} />

        <aside className="changes-panel">
          <h3>What changed</h3>
          {pkg.changes.length ? (
            pkg.changes.map((c) => (
              <details key={c.id}>
                <summary>
                  Reworded experience <ChevronRight size={14} />
                </summary>
                <h4>Original</h4>
                <p>{c.before}</p>
                <h4>Tailored</h4>
                <p>{c.after}</p>
              </details>
            ))
          ) : (
            <p>
              All experience statements retain their source wording. Skill groups are ordered by
              relevance.
            </p>
          )}

          <Notice>Check every statement before approving. AI checks can miss unsupported claims.</Notice>

          <label className="check-field">
            <input
              type="checkbox"
              checked={cvChecked}
              disabled={isLocked || isSaving}
              onChange={(e) => setCVChecked(e.target.checked)}
            />
            <span>I reviewed the complete CV and confirm its statements are accurate.</span>
          </label>

          <Button
            disabled={isLocked || !isDirty || isSaving}
            loading={isSaving}
            kind="primary"
            onClick={() => void handleSaveReview()}
          >
            Save CV review
            <Check size={15} />
          </Button>
        </aside>
      </div>
    </>
  )
}
