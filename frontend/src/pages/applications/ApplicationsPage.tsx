import { Link, useOutletContext } from 'react-router-dom'
import { Clock3, ChevronRight, ArrowRight } from 'lucide-react'
import { Badge } from '../../shared/ui/Badge'
import { Notice } from '../../shared/ui/Notice'
import { Empty } from '../../shared/ui/Empty'
import { formatDate, STATE_LABELS } from '../../shared/lib/formatters'
import type { Bootstrap } from '../../types'

export function ApplicationsPage() {
  const { data } = useOutletContext<{ data?: Bootstrap }>()

  const jobs = data?.jobs || []
  const events = data?.events || []
  const failedRuns =
    data?.runs?.filter((r) => ['failed', 'interrupted'].includes(r.state)) || []

  return (
    <>
      <div className="page-heading">
        <div>
          <h1>Keep the story moving.</h1>
          <p>Every review, application, and next step in one place.</p>
        </div>
      </div>

      {/* Tracker Status Counts */}
      <div className="tracker-counts" role="region" aria-label="Application state summary">
        {(['awaiting_review', 'approved', 'submitted', 'needs_input'] as const).map((s) => (
          <div key={s}>
            <span>{STATE_LABELS[s]}</span>
            <strong>{jobs.filter((j) => j.state === s).length}</strong>
          </div>
        ))}
      </div>

      {/* Tracked Jobs List */}
      {jobs.length > 0 ? (
        <ul className="tracker-list" style={{ listStyle: 'none', margin: 0, padding: '0 24px' }}>
          {jobs.map((j, idx) => (
            <li key={j.id} style={{ listStyle: 'none' }}>
              <Link
                to={`/jobs/${j.id}/application`}
                className="tracker-row"
                style={{
                  textDecoration: 'none',
                  borderBottom: idx === jobs.length - 1 ? 0 : undefined,
                }}
              >
                <span>
                  <strong>{j.title}</strong>
                  <small>{j.company}</small>
                </span>
                <Badge state={j.state} />
                <span>{formatDate(j.created)}</span>
                <ChevronRight size={16} aria-hidden="true" />
              </Link>
            </li>
          ))}
        </ul>
      ) : (
        <Empty
          title="A clear view of what’s next"
          action={
            <Link to="/opportunities" className="button primary">
              Add an opportunity
              <ArrowRight size={16} />
            </Link>
          }
        >
          Saved jobs and applications will appear here as you work through them.
        </Empty>
      )}

      {/* Recent Global Activity */}
      <section className="activity" aria-label="Workspace activity log">
        <h2>Recent activity</h2>
        {events.length > 0 ? (
          events.slice(0, 15).map((e) => (
            <div className="activity-row" key={e.id}>
              <Clock3 size={15} aria-hidden="true" />
              <p>{e.text}</p>
              <small>{formatDate(e.created)}</small>
            </div>
          ))
        ) : (
          <p className="muted">Your application history starts with your first saved job.</p>
        )}

        {failedRuns.map((r) => {
          const targetJob = r.target ? jobs.find((j) => j.id === r.target) : undefined
          return (
            <Notice key={r.id} kind="error">
              <div style={{ display: 'flex', flexDirection: 'column', gap: 6, width: '100%' }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 8 }}>
                  <span>
                    <strong>Operation failed:</strong>{' '}
                    {targetJob ? (
                      <Link to={`/jobs/${targetJob.id}/description`} style={{ fontWeight: 700 }}>
                        {targetJob.title} ({targetJob.company})
                      </Link>
                    ) : (
                      r.kind
                    )}
                  </span>
                  {targetJob && (
                    <Link to={`/jobs/${targetJob.id}/description`} className="text-button" style={{ padding: 0, minHeight: 'auto' }}>
                      View job details →
                    </Link>
                  )}
                </div>
                <p style={{ margin: 0 }}>{r.message}</p>
              </div>
            </Notice>
          )
        })}
      </section>
    </>
  )
}
