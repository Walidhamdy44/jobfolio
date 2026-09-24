import { useOutletContext } from 'react-router-dom'
import { ExternalLink } from 'lucide-react'
import { formatDate } from '../../shared/lib/formatters'
import type { Job, Event } from '../../types'

export function JobActivityPage() {
  const { job, events } = useOutletContext<{
    job: Job
    events: Event[]
  }>()

  return (
    <div style={{ maxWidth: '800px' }}>
      <div className="section-title">
        <div>
          <h2>Application activity & events</h2>
          <p className="muted">Chronological audit trail of actions taken for this opportunity.</p>
        </div>
      </div>

      {job.receipt && (
        <div
          style={{
            padding: '18px',
            background: 'var(--color-surface)',
            border: '1px solid var(--color-border)',
            borderRadius: '8px',
            marginBottom: '24px',
          }}
        >
          <h3 style={{ marginBottom: '8px' }}>
            {job.receipt.manual ? 'Manual submission recorded' : 'Submission confirmation'}
          </h3>
          <p style={{ fontSize: '12px', color: 'var(--color-text-muted)' }}>{job.receipt.text}</p>
          <small style={{ display: 'block', marginTop: '6px' }}>
            Recorded on {formatDate(job.receipt.at)}
          </small>

          {job.receipt.path && (
            <a
              href={`/api/jobs/${job.id}/receipt`}
              target="_blank"
              rel="noreferrer"
              className="text-button"
              style={{ marginTop: '10px' }}
            >
              Open confirmation screenshot
              <ExternalLink size={14} />
            </a>
          )}
        </div>
      )}

      <div className="detail-history" style={{ marginTop: 0, borderTop: 0, paddingTop: 0 }}>
        {events && events.length > 0 ? (
          events.map((e) => (
            <div key={e.id}>
              <span aria-hidden="true" />
              <p style={{ margin: 0 }}>{e.text}</p>
              <small>{formatDate(e.created)}</small>
            </div>
          ))
        ) : (
          <p className="muted">No activity recorded for this job yet.</p>
        )}
      </div>
    </div>
  )
}
