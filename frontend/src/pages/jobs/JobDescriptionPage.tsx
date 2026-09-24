import { useState } from 'react'
import { useOutletContext } from 'react-router-dom'
import { Edit3, RefreshCw } from 'lucide-react'
import { Button } from '../../shared/ui/Button'
import { Notice } from '../../shared/ui/Notice'
import {
  useSkipJobMutation,
  useUpdateJobMutation,
  useRefetchJobMutation,
} from '../../features/jobs/queries'
import { formatDate } from '../../shared/lib/formatters'
import type { Job, Package } from '../../types'

function getSourceLabel(job: Job) {
  if (job.source) return job.source
  if (!job.url || job.platform === 'pasted') return 'Pasted description'
  if (job.platform === 'greenhouse') return 'Greenhouse board'
  if (job.platform === 'lever') return 'Lever board'
  if (['jobicy', 'remotive', 'arbeitnow', 'weworkremotely'].includes(job.platform)) {
    return `${job.platform.charAt(0).toUpperCase() + job.platform.slice(1)} feed`
  }
  return 'Employer website'
}

export function JobDescriptionPage() {
  const { job, isLocked, setToast } = useOutletContext<{
    job: Job
    pkg: Package | null
    isLocked: boolean
    setToast: (msg: string) => void
  }>()

  const [isEditing, setIsEditing] = useState(false)
  const [descriptionDraft, setDescriptionDraft] = useState(job.description)

  const skipMutation = useSkipJobMutation(job.id)
  const updateMutation = useUpdateJobMutation(job.id)
  const refetchMutation = useRefetchJobMutation(job.id)

  const handleSkip = async () => {
    try {
      await skipMutation.mutateAsync()
      setToast('Job marked as skipped.')
    } catch (e) {
      setToast((e as Error).message)
    }
  }

  const handleSaveDescription = async () => {
    if (!descriptionDraft.trim()) {
      setToast('Description cannot be empty.')
      return
    }
    try {
      await updateMutation.mutateAsync({ description: descriptionDraft.trim() })
      setIsEditing(false)
      setToast('Job description updated successfully.')
    } catch (e) {
      setToast((e as Error).message)
    }
  }

  const handleRefetch = async () => {
    try {
      await refetchMutation.mutateAsync()
      setToast('Re-fetched full job posting from employer URL.')
    } catch (e) {
      setToast((e as Error).message)
    }
  }

  const isIncomplete = job.description.length < 250
  const hasError = Boolean(job.last_error)

  return (
    <div className="description-layout">
      <article className="job-description">
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '15px' }}>
          <h2>About this role</h2>
          <div className="button-group">
            {job.url && !isLocked && (
              <Button
                disabled={refetchMutation.isPending}
                loading={refetchMutation.isPending}
                onClick={() => void handleRefetch()}
                title="Fetch complete description from the posting URL"
              >
                <RefreshCw size={14} />
                Retry fetching description
              </Button>
            )}
            {!isLocked && !isEditing && (
              <Button onClick={() => { setDescriptionDraft(job.description); setIsEditing(true) }}>
                <Edit3 size={14} />
                Edit / Paste full description
              </Button>
            )}
          </div>
        </div>

        {isIncomplete && !isEditing && (
          <Notice kind="warning">
            <strong>Incomplete or brief description:</strong>{' '}
            This job has only a brief summary and lacks detailed responsibilities or qualifications. Click &quot;Edit / Paste full description&quot; or &quot;Retry fetching description&quot; so your CV can be tailored.
          </Notice>
        )}

        {hasError && !isIncomplete && !isEditing && (
          <Notice kind="warning">
            <strong>Recent operation note:</strong>{' '}
            {job.last_error}
          </Notice>
        )}

        {isEditing ? (
          <div style={{ marginTop: '20px' }}>
            <label htmlFor="edit-job-description" style={{ display: 'block', marginBottom: '8px', fontSize: '12px', fontWeight: 650 }}>
              Full job description (responsibilities, required & preferred qualifications)
            </label>
            <textarea
              id="edit-job-description"
              rows={16}
              value={descriptionDraft}
              onChange={(e) => setDescriptionDraft(e.target.value)}
              style={{
                width: '100%',
                padding: '12px',
                fontFamily: 'inherit',
                fontSize: '13px',
                lineHeight: 1.6,
                borderRadius: '6px',
                border: '1px solid var(--line, #cbd9cf)',
                background: '#fff',
              }}
              placeholder="Paste full responsibilities, requirements, and preferred qualifications here..."
            />
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '12px' }}>
              <span className="small muted">{descriptionDraft.length} characters</span>
              <div className="button-group">
                <Button
                  disabled={updateMutation.isPending}
                  onClick={() => { setDescriptionDraft(job.description); setIsEditing(false) }}
                >
                  Cancel
                </Button>
                <Button
                  kind="primary"
                  disabled={updateMutation.isPending || !descriptionDraft.trim()}
                  loading={updateMutation.isPending}
                  onClick={() => void handleSaveDescription()}
                >
                  Save description
                </Button>
              </div>
            </div>
          </div>
        ) : (
          <p>{job.description}</p>
        )}
      </article>

      <aside className="detail-aside">
        <h3>Posting details</h3>
        <dl>
          <dt>Source</dt>
          <dd>{getSourceLabel(job)}</dd>
          <dt>Saved</dt>
          <dd>{formatDate(job.created)}</dd>
          <dt>Availability</dt>
          <dd>{job.verified ? 'Verified when imported' : 'Needs confirmation'}</dd>
        </dl>
        <p>
          {job.verification_note ||
            'The agent checks the posting before preparing an application.'}
        </p>

        {job.state !== 'skipped' && (
          <Button
            disabled={skipMutation.isPending || isLocked}
            loading={skipMutation.isPending}
            onClick={() => void handleSkip()}
          >
            Skip this job
          </Button>
        )}
      </aside>
    </div>
  )
}
