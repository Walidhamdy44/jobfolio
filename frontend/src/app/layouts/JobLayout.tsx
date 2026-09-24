import { useParams, NavLink, Outlet, Link, useOutletContext } from 'react-router-dom'
import {
  ArrowLeft,
  ArrowUpRight,
  FileText,
  Sparkles,
  MapPin,
  ChevronRight,
  Download,
} from 'lucide-react'
import { useJobDetailQuery, usePrepareJobMutation, useCoverLetterMutation } from '../../features/jobs/queries'
import { ReviewDraftProvider } from '../../features/review/ReviewDraftContext'
import { Badge } from '../../shared/ui/Badge'
import { Button } from '../../shared/ui/Button'
import { Notice } from '../../shared/ui/Notice'
import { Empty } from '../../shared/ui/Empty'
import type { Bootstrap } from '../../types'

export function JobLayout() {
  const { jobId } = useParams<{ jobId: string }>()
  const { data: bootstrap, setToast } = useOutletContext<{
    data?: Bootstrap
    setToast: (msg: string) => void
  }>()

  const { data: detail, isLoading, error } = useJobDetailQuery(jobId)

  const prepareMutation = usePrepareJobMutation(jobId || '')
  const coverLetterMutation = useCoverLetterMutation(jobId || '')

  if (isLoading) {
    return (
      <div className="detail-workbench">
        <Link to="/opportunities" className="text-button back-button">
          <ArrowLeft size={16} />
          Back to opportunities
        </Link>
        <p className="muted">Loading job details…</p>
      </div>
    )
  }

  if (error || !detail?.job) {
    return (
      <div className="detail-workbench">
        <Link to="/opportunities" className="text-button back-button">
          <ArrowLeft size={16} />
          Back to opportunities
        </Link>
        <Empty title="Job not found" icon="jobs">
          This job may have been removed or does not exist in your workspace.
        </Empty>
      </div>
    )
  }

  const { job, package: pkg, events } = detail
  const isAiConnected = Boolean(bootstrap?.connections?.connected)
  const isLocked = ['submitted', 'submitting', 'uncertain'].includes(job.state)

  const handlePrepare = async (mode: 'ai' | 'local') => {
    try {
      await prepareMutation.mutateAsync({ mode })
      setToast(mode === 'ai' ? 'AI CV tailoring started.' : 'Local CV preparation started.')
    } catch (e) {
      setToast((e as Error).message)
    }
  }

  const handleCoverLetter = async () => {
    try {
      await coverLetterMutation.mutateAsync({ mode: isAiConnected ? 'ai' : 'local' })
      setToast('Cover letter drafting started.')
    } catch (e) {
      setToast((e as Error).message)
    }
  }

  return (
    <ReviewDraftProvider jobId={job.id} pkg={pkg}>
      <section className="detail-workbench" aria-label={`Job details for ${job.title} at ${job.company}`}>
        <Link to="/opportunities" className="text-button back-button">
          <ArrowLeft size={16} />
          Back to opportunities
        </Link>

        {/* Job Identity Heading */}
        <div className="detail-heading">
          <span className="company-avatar large">
            {job.company.slice(0, 2).toUpperCase()}
          </span>
          <div>
            <h1>{job.title}</h1>
            <p>
              {job.company}
              <span>·</span>
              <MapPin size={14} aria-hidden="true" />
              {job.location || 'Location needs confirmation'}
            </p>
          </div>
          <Badge state={job.state} />
        </div>

        {/* Action Toolbar */}
        <div className="detail-toolbar">
          {job.url && (
            <a className="button" href={job.url} target="_blank" rel="noreferrer">
              View posting
              <ArrowUpRight size={15} />
            </a>
          )}

          {!isLocked && (
            <>
              <Button
                disabled={prepareMutation.isPending}
                loading={prepareMutation.isPending && prepareMutation.variables?.mode === 'local'}
                onClick={() => void handlePrepare('local')}
              >
                <FileText size={15} />
                {pkg ? 'Rebuild local CV' : 'Prepare local CV'}
              </Button>

              <Button
                kind="primary"
                disabled={prepareMutation.isPending || !isAiConnected}
                loading={prepareMutation.isPending && prepareMutation.variables?.mode === 'ai'}
                onClick={() => void handlePrepare('ai')}
              >
                <Sparkles size={15} />
                Tailor with AI
              </Button>
            </>
          )}

          {!isAiConnected && !isLocked && (
            <small>
              Connect an AI provider in{' '}
              <Link to="/settings/ai" style={{ textDecoration: 'underline' }}>
                Connections
              </Link>{' '}
              to enable AI tailoring (free models supported).
            </small>
          )}
        </div>

        {/* Cover letter actions */}
        {pkg && !isLocked && (
          <div className="cover-letter-tools">
            <Button
              disabled={coverLetterMutation.isPending}
              loading={coverLetterMutation.isPending}
              onClick={() => void handleCoverLetter()}
            >
              <FileText size={15} />
              {pkg.cover_letter ? 'Redraft cover letter' : 'Draft a cover letter'}
            </Button>
            <small>
              {isAiConnected
                ? 'Uses confirmed CV evidence and job context.'
                : 'Creates a local draft from your CV summary.'}
            </small>
          </div>
        )}

        {/* Filter notes and warnings */}
        {job.filter_notes && job.filter_notes.length > 0 && (
          <Notice>
            {job.filter_notes.map((n) => (
              <div key={n}>{n}</div>
            ))}
          </Notice>
        )}

        {pkg && bootstrap?.profile && pkg.profile_revision !== bootstrap.profile.revision && (
          <Notice kind="warning">
            Your master profile changed since this package was prepared. Prepare a fresh CV before approval.
          </Notice>
        )}

        {job.state === 'uncertain' && (
          <Notice kind="warning">
            Submission status could not be verified automatically. Check with the employer or your email before recording the outcome.
          </Notice>
        )}

        {/* Nested Navigation Tabs (Real Links!) */}
        <nav className="detail-tabs" aria-label="Job review navigation">
          <NavLink
            to={`/jobs/${job.id}/description`}
            className={({ isActive }) => (isActive ? 'active' : '')}
            aria-current={location.pathname.endsWith('/description') ? 'page' : undefined}
          >
            Job description
          </NavLink>
          <NavLink
            to={`/jobs/${job.id}/cv`}
            className={({ isActive }) => (isActive ? 'active' : '')}
            aria-current={location.pathname.endsWith('/cv') ? 'page' : undefined}
          >
            Tailored CV
          </NavLink>
          <NavLink
            to={`/jobs/${job.id}/coverage`}
            className={({ isActive }) => (isActive ? 'active' : '')}
            aria-current={location.pathname.endsWith('/coverage') ? 'page' : undefined}
          >
            Requirement coverage
            {pkg && <span>{pkg.score}%</span>}
          </NavLink>
          <NavLink
            to={`/jobs/${job.id}/application`}
            className={({ isActive }) => (isActive ? 'active' : '')}
            aria-current={location.pathname.endsWith('/application') ? 'page' : undefined}
          >
            Application
          </NavLink>
          <NavLink
            to={`/jobs/${job.id}/activity`}
            className={({ isActive }) => (isActive ? 'active' : '')}
            aria-current={location.pathname.endsWith('/activity') ? 'page' : undefined}
          >
            Activity & History
          </NavLink>
        </nav>

        {/* Cover letter banner preview */}
        {pkg?.cover_letter && (
          <details className="cover-letter-preview">
            <summary>
              Cover letter included in this package
              <ChevronRight size={15} />
            </summary>
            <p>{pkg.cover_letter}</p>
            <div className="button-group">
              <a
                className="button"
                href={`/api/jobs/${job.id}/documents/cover_letter_pdf`}
                download
              >
                <Download size={15} />
                Letter PDF
              </a>
              <a
                className="button"
                href={`/api/jobs/${job.id}/documents/cover_letter_docx`}
                download
              >
                Letter Word
              </a>
            </div>
            <small>Review this letter before approving the application package.</small>
          </details>
        )}

        {/* Child Route Content */}
        <div className="tab-content">
          <Outlet context={{ job, pkg, events, bootstrap, setToast, isLocked }} />
        </div>
      </section>
    </ReviewDraftProvider>
  )
}
