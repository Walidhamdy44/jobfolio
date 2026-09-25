import React, { useState } from 'react'
import { useOutletContext } from 'react-router-dom'
import {
  CheckCircle2,
  Circle,
  ShieldCheck,
  Send,
  ExternalLink,
  ListChecks,
  ChevronRight,
  Check,
  Sparkles,
} from 'lucide-react'
import { DynamicField } from '../../features/applications/components/DynamicField'
import { useReviewDraft } from '../../features/review/ReviewDraftContext'
import {
  useInspectJobMutation,
  useApproveJobMutation,
  useSubmitJobMutation,
  useResolveJobMutation,
  useAutoApplyJobMutation,
  useOpenBrowserSessionMutation,
} from '../../features/jobs/queries'
import { Button } from '../../shared/ui/Button'
import { Badge } from '../../shared/ui/Badge'
import { Notice } from '../../shared/ui/Notice'
import { Field } from '../../shared/ui/Field'
import type { Job, Package } from '../../types'

export function JobApplicationPage() {
  const { job, pkg, isLocked, setToast } = useOutletContext<{
    job: Job
    pkg: Package | null
    isLocked: boolean
    setToast: (msg: string) => void
  }>()

  const { answers, setAnswer, isDirty, saveReview, isSaving } = useReviewDraft()

  const [resolutionOpen, setResolutionOpen] = useState(false)
  const [resolutionStatus, setResolutionStatus] = useState<'submitted' | 'not_submitted'>('submitted')
  const [resolutionNote, setResolutionNote] = useState('')
  const [coPilotMode, setCoPilotMode] = useState(true)
  const isAutomated = ['greenhouse', 'lever'].includes(job.platform)
  const isLinkedIn = job.platform === 'linkedin'

  const inspectMutation = useInspectJobMutation(job.id)
  const approveMutation = useApproveJobMutation(job.id)
  const submitMutation = useSubmitJobMutation(job.id)
  const resolveMutation = useResolveJobMutation(job.id)
  const autoApplyMutation = useAutoApplyJobMutation(job.id)
  const openSessionMutation = useOpenBrowserSessionMutation()

  const handleInspect = async () => {
    try {
      await inspectMutation.mutateAsync()
      setToast('Reading application form questions…')
    } catch (e) {
      setToast((e as Error).message)
    }
  }

  const handleSaveAnswers = async () => {
    try {
      await saveReview()
      setToast('Answers saved.')
    } catch (e) {
      setToast((e as Error).message)
    }
  }

  const handleApprove = async () => {
    if (!pkg) return
    try {
      await approveMutation.mutateAsync({ package_hash: pkg.hash })
      setToast('Package approved. No application has been sent yet.')
    } catch (e) {
      setToast((e as Error).message)
    }
  }

  const handleSubmitApplication = async () => {
    if (!pkg) return
    try {
      await submitMutation.mutateAsync({ package_hash: pkg.hash })
      setToast('Approved submission started.')
    } catch (e) {
      setToast((e as Error).message)
    }
  }

  const handleAutoApply = async () => {
    if (!pkg) return
    if (!pkg.approved) {
      setToast('Please review and approve this package before launching AI Auto-Apply.')
      return
    }
    try {
      await autoApplyMutation.mutateAsync({
        package_hash: pkg.hash,
        auto_submit: !coPilotMode,
        headless: false,
      })
      setToast(
        coPilotMode
          ? 'AI Auto-Apply launched! Watch your browser window as the agent fills answers.'
          : 'AI Auto-Apply launched in automated submission mode.'
      )
    } catch (e) {
      setToast((e as Error).message)
    }
  }

  const handleOpenSession = async () => {
    try {
      await openSessionMutation.mutateAsync({ url: job.url || 'https://www.linkedin.com' })
      setToast('Browser window opened. Log into your account and keep it saved.')
    } catch (e) {
      setToast((e as Error).message)
    }
  }

  const handleResolve = async (e: React.FormEvent) => {
    e.preventDefault()
    try {
      await resolveMutation.mutateAsync({
        status: resolutionStatus,
        note: resolutionNote,
      })
      setToast('Application status recorded.')
      setResolutionOpen(false)
      setResolutionNote('')
    } catch (e) {
      setToast((e as Error).message)
    }
  }

  return (
    <>
      <div className="section-title">
        <div>
          <h2>Your application, ready for a final look.</h2>
          <p className="muted">Approval covers your tailored CV and the answers below.</p>
        </div>
        <Badge state={job.state} />
      </div>

      {job.receipt && (
        <Notice kind="success">
          <strong>{job.receipt.manual ? 'Submission recorded by you' : 'Submission confirmed'}</strong>
          <p>{job.receipt.text}</p>
          {job.receipt.path && (
            <a
              href={`/api/jobs/${job.id}/receipt`}
              target="_blank"
              rel="noreferrer"
              style={{ display: 'inline-block', marginTop: '6px' }}
            >
              View confirmation screenshot
            </a>
          )}
        </Notice>
      )}

      <div className="application-layout">
        {/* Form Questions Area */}
        <section>
          <h3>Application questions</h3>

          {!pkg?.form ? (
            <>
              <p className="muted">
                {!isAutomated
                  ? isLinkedIn
                    ? 'LinkedIn Easy Apply is handled by the Co-Pilot below after you review and approve the CV. You can also apply manually and record the outcome here.'
                    : 'This site needs a manual application. Download your CV, open the posting, and record the result here.'
                  : 'Read the employer’s form to prepare answers before approval. Some forms require a manual handoff.'}
              </p>
              {isAutomated && (
                <Button
                  disabled={isLocked || inspectMutation.isPending}
                  loading={inspectMutation.isPending}
                  onClick={() => void handleInspect()}
                >
                  <ListChecks size={16} />
                  Read application form
                </Button>
              )}
            </>
          ) : (
            <div className="application-fields">
              {pkg.form.fields.map((f) => (
                <DynamicField
                  key={f.key}
                  field={f}
                  value={answers[f.key] || ''}
                  disabled={isLocked || isSaving}
                  onChange={(val) => setAnswer(f.key, val)}
                />
              ))}

              <Button
                disabled={isLocked || !isDirty || isSaving}
                loading={isSaving}
                onClick={() => void handleSaveAnswers()}
              >
                Save answers
                <Check size={15} />
              </Button>
            </div>
          )}
        </section>

        {/* Approval and Submission Gate Panel */}
        <aside className="approval-panel">
          <h3>Before you submit</h3>

          <div className="checklist-line" aria-label={`CV reviewed: ${pkg?.cv_reviewed ? 'Completed' : 'Pending'}`}>
            {pkg?.cv_reviewed ? (
              <CheckCircle2 size={18} aria-hidden="true" />
            ) : (
              <Circle size={18} aria-hidden="true" />
            )}
            <span>CV reviewed</span>
            <span className="sr-only">({pkg?.cv_reviewed ? 'Completed' : 'Pending'})</span>
          </div>
          <div className="checklist-line" aria-label={`Coverage and gaps reviewed: ${pkg?.coverage_reviewed ? 'Completed' : 'Pending'}`}>
            {pkg?.coverage_reviewed ? (
              <CheckCircle2 size={18} aria-hidden="true" />
            ) : (
              <Circle size={18} aria-hidden="true" />
            )}
            <span>Coverage and gaps reviewed</span>
            <span className="sr-only">({pkg?.coverage_reviewed ? 'Completed' : 'Pending'})</span>
          </div>
          <div className="checklist-line" aria-label={`Current package approved: ${pkg?.approved ? 'Completed' : 'Pending'}`}>
            {pkg?.approved ? (
              <CheckCircle2 size={18} aria-hidden="true" />
            ) : (
              <Circle size={18} aria-hidden="true" />
            )}
            <span>Current package approved</span>
            <span className="sr-only">({pkg?.approved ? 'Completed' : 'Pending'})</span>
          </div>

          {pkg && (
            <p>
              Your CV covers <strong>{pkg.score}%</strong> of the weighted requirements. You can
              approve a truthful CV below 95%.
            </p>
          )}

          {isDirty && (
            <Notice kind="warning">Save your latest review changes before approving.</Notice>
          )}

          <Button
            kind="primary"
            disabled={
              isLocked ||
              isDirty ||
              !pkg?.cv_reviewed ||
              !pkg?.coverage_reviewed ||
              pkg?.approved ||
              approveMutation.isPending
            }
            loading={approveMutation.isPending}
            onClick={() => void handleApprove()}
          >
            <ShieldCheck size={16} />
            Approve this package
          </Button>

          {isAutomated && (
            <Button
              kind="submit-button"
              disabled={
                isLocked ||
                isDirty ||
                !pkg?.approved ||
                !pkg?.form ||
                submitMutation.isPending
              }
              loading={submitMutation.isPending}
              onClick={() => void handleSubmitApplication()}
            >
              <Send size={16} />
              Submit application
            </Button>
          )}

          <p className="small">
            {isAutomated
              ? 'Selecting Submit sends your approved CV and answers to the employer.'
              : job.url
              ? 'Apply on the employer site, then record the outcome below.'
              : 'Open the original employer application page yourself, use your downloaded CV, then record the outcome below.'}
          </p>

          {job.url && (
            <a className="text-button" href={job.url} target="_blank" rel="noreferrer">
              Open employer site in a new tab (manual)
              <ExternalLink size={14} />
            </a>
          )}

          <div style={{ marginTop: '22px', paddingTop: '16px', borderTop: '1px solid #c8d8cb' }}>
            <h4 style={{ display: 'flex', alignItems: 'center', gap: '7px', color: '#254e38', marginBottom: '8px', fontSize: '12px' }}>
              <Sparkles size={16} color="#357a55" />
              AI Auto-Apply Co-Pilot
            </h4>
            <p className="small" style={{ marginBottom: '10px' }}>
              Opens a separate controlled browser window, fills supported answers, and uploads your tailored CV. It stays open when you need to answer a question or review the form before submission.
            </p>

            <label className="check-field" style={{ margin: '8px 0 14px', fontSize: '11px' }}>
              <input type="checkbox" checked={coPilotMode} onChange={(e) => setCoPilotMode(e.target.checked)} disabled />
              <span>Co-Pilot mode (review form in browser before final submit)</span>
            </label>
            <p className="small muted">Unattended submission is unavailable while screening answers require your review.</p>

            <Button
              kind="primary"
              disabled={isLocked || isDirty || !pkg?.approved || autoApplyMutation.isPending}
              loading={autoApplyMutation.isPending}
              onClick={() => void handleAutoApply()}
              style={{ width: '100%', marginBottom: '8px' }}
            >
              <Sparkles size={15} />
              {autoApplyMutation.isPending
                ? 'Auto-Applying…'
                : coPilotMode
                ? 'Launch AI Auto-Apply (Co-Pilot)'
                : 'Launch Full Auto-Apply'}
            </Button>
            {!pkg?.approved && (
              <p className="small muted" style={{ margin: '4px 0 8px', fontSize: '11px', textAlign: 'center' }}>
                Approve this tailored package above to enable Auto-Apply.
              </p>
            )}

            <button
              type="button"
              className="text-button"
              style={{ fontSize: '11px', marginTop: '6px', width: '100%', justifyContent: 'center' }}
              onClick={() => void handleOpenSession()}
              disabled={openSessionMutation.isPending}
            >
              <ExternalLink size={13} />
              Open the separate agent browser to sign in
            </button>
          </div>
        </aside>
      </div>

      {/* Manual Resolution Section */}
      {job.state !== 'submitting' && job.state !== 'submitted' && (
        <div className="manual-resolution">
          <button
            type="button"
            className="text-button"
            onClick={() => setResolutionOpen(!resolutionOpen)}
          >
            Applied manually or checked an uncertain result?
            <ChevronRight size={15} />
          </button>

          {resolutionOpen && (
            <form onSubmit={handleResolve}>
              <Field label="Confirmed outcome">
                <select
                  value={resolutionStatus}
                  onChange={(e) =>
                    setResolutionStatus(e.target.value as 'submitted' | 'not_submitted')
                  }
                >
                  <option value="submitted">I confirmed the application was submitted</option>
                  <option value="not_submitted">I confirmed no application was submitted</option>
                </select>
              </Field>

              <Field
                label="Confirmation details"
                hint="Record the confirmation message, reference, or how you verified."
                required
              >
                <textarea
                  required
                  minLength={10}
                  rows={3}
                  value={resolutionNote}
                  onChange={(e) => setResolutionNote(e.target.value)}
                  placeholder="Enter confirmation email details, application ID, or notes…"
                />
              </Field>

              <Button type="submit" disabled={resolveMutation.isPending} loading={resolveMutation.isPending}>
                Record outcome
              </Button>
            </form>
          )}
        </div>
      )}
    </>
  )
}
