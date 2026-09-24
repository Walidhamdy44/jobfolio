import { useState } from 'react'
import { Link, useSearchParams, useOutletContext, useNavigate } from 'react-router-dom'
import {
  Plus,
  Search,
  SlidersHorizontal,
  ChevronRight,
  CheckCircle2,
  Circle,
  CircleHelp,
  ArrowRight,
} from 'lucide-react'
import { Button } from '../../shared/ui/Button'
import { Badge } from '../../shared/ui/Badge'
import { Empty } from '../../shared/ui/Empty'
import { AddJobForm } from '../../features/jobs/components/AddJobForm'
import { useAddJobMutation, useImportJobMutation } from '../../features/jobs/queries'
import type { Bootstrap } from '../../types'

export function OpportunitiesPage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const navigate = useNavigate()
  const { data, setToast } = useOutletContext<{
    data?: Bootstrap
    setToast: (msg: string) => void
  }>()

  const [adding, setAdding] = useState(false)

  const addJobMutation = useAddJobMutation()
  const importJobMutation = useImportJobMutation()

  const filter = searchParams.get('status') || 'all'
  const query = searchParams.get('q') || ''

  const setFilter = (newFilter: string) => {
    setSearchParams((prev) => {
      const p = new URLSearchParams(prev)
      p.set('status', newFilter)
      return p
    })
  }

  const setQuery = (newQuery: string) => {
    setSearchParams((prev) => {
      const p = new URLSearchParams(prev)
      if (newQuery) p.set('q', newQuery)
      else p.delete('q')
      return p
    })
  }

  const jobs = data?.jobs || []
  const queryTrimmed = query.trim().toLowerCase()
  const visibleJobs = jobs
    .filter((j) => {
      if (filter === 'all') return j.state !== 'skipped'
      if (filter === 'review') return ['awaiting_review', 'needs_input', 'uncertain'].includes(j.state)
      return j.state === filter
    })
    .filter((j) => (j.title + ' ' + j.company).toLowerCase().includes(queryTrimmed))

  const handleSave = async (jobData: {
    url: string
    title: string
    company: string
    location: string
    description: string
  }) => {
    try {
      const res = await addJobMutation.mutateAsync(jobData)
      setAdding(false)
      setToast('Job saved.')
      if (res.job?.id) {
        navigate(`/jobs/${res.job.id}/description`)
      }
    } catch (e) {
      setToast((e as Error).message)
    }
  }

  const handleImport = async (url: string) => {
    try {
      const res = await importJobMutation.mutateAsync({ url })
      setAdding(false)
      setToast(res.job.verified
        ? 'Full job posting imported. Review it before preparing a CV.'
        : 'Job saved from a brief summary. Preparing a CV will first retry fetching the full posting.')
      if (res.job?.id) {
        navigate(`/jobs/${res.job.id}/description`)
      }
    } catch (e) {
      setToast((e as Error).message)
    }
  }

  return (
    <>
      <div className="page-heading">
        <div>
          <h1>Your next chapter.</h1>
          <p>Find the right opportunity. Make every application count.</p>
        </div>
        <Button onClick={() => setAdding(!adding)}>
          <Plus size={17} />
          Add a job
        </Button>
      </div>

      {adding && (
        <AddJobForm
          busy={addJobMutation.isPending || importJobMutation.isPending}
          onClose={() => setAdding(false)}
          onSave={handleSave}
          onImport={handleImport}
        />
      )}

      <div className="overview-layout">
        <section className="queue-area">
          {/* Quick Discover Callout */}
          <div className="search-launch">
            <div className="search-launch-icon">
              <Search size={23} />
            </div>
            <div>
              <h2>A search shaped around you</h2>
              <p>{data?.preferences.titles.slice(0, 3).join(' · ') || 'Frontend Engineer'}</p>
              <small>
                {data?.preferences.confirmed
                  ? `${data.preferences.location ? `${data.preferences.location} · ` : ''}${
                      data.connections.search_provider === 'free'
                        ? 'LinkedIn Jobs & curated feeds active'
                        : data.connections.search_provider === 'serper'
                        ? 'Google Jobs active'
                        : 'Brave Search active'
                    }`
                  : 'Review your location and preferences before searching'}
              </small>
            </div>
            <Link to="/discover" className="button primary">
              <Search size={16} />
              Find jobs
            </Link>
          </div>

          <div className="section-title queue-title">
            <h2>
              Your opportunities <span>{jobs.filter((j) => j.state !== 'skipped').length}</span>
            </h2>
            <Link to="/preferences" className="text-button">
              <SlidersHorizontal size={15} />
              Preferences
            </Link>
          </div>

          <div className="queue-tools">
            <div className="filter-tabs" aria-label="Filter jobs">
              {[
                ['all', 'All jobs'],
                ['review', 'To review'],
                ['approved', 'Approved'],
                ['skipped', 'Skipped'],
              ].map(([k, v]) => (
                <button
                  key={k}
                  type="button"
                  className={filter === k ? 'selected' : ''}
                  aria-pressed={filter === k}
                  onClick={() => setFilter(k)}
                >
                  {v}
                </button>
              ))}
            </div>
            <div className="inline-search">
              <Search size={15} />
              <input
                aria-label="Filter by title or company"
                placeholder="Title or company"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
              />
            </div>
          </div>

          {visibleJobs.length ? (
            <div className="job-list" role="list">
              {visibleJobs.map((j) => (
                <Link
                  to={`/jobs/${j.id}/description`}
                  className="job-row"
                  key={j.id}
                  style={{ textDecoration: 'none', color: 'inherit' }}
                >
                  <span className="company-avatar">{j.company.slice(0, 2).toUpperCase()}</span>
                  <span className="job-main">
                    <strong>{j.title}</strong>
                    <span>
                      {j.company}
                      <i>·</i>
                      {j.location || 'Location not confirmed'}
                    </span>
                    <Badge state={j.state} />
                  </span>
                  <span className="job-meta">
                    {j.score !== undefined ? (
                      <>
                        <b>{j.score}%</b>
                        <small>CV coverage</small>
                      </>
                    ) : !j.verified && j.url ? (
                      <small style={{ color: 'var(--color-danger, #ef4444)' }}>Needs full description</small>
                    ) : j.last_error ? (
                      <small style={{ color: 'var(--color-danger, #ef4444)' }}>Needs attention</small>
                    ) : (
                      <small>Ready to prepare</small>
                    )}
                    <ChevronRight size={17} />
                  </span>
                </Link>
              ))}
            </div>
          ) : (
            <Empty
              title={jobs.length ? 'No jobs in this view' : 'Your next opportunity belongs here'}
              action={
                jobs.length ? (
                  <Button
                    onClick={() => {
                      setFilter('all')
                      setQuery('')
                    }}
                  >
                    Clear filter
                  </Button>
                ) : (
                  <Button onClick={() => setAdding(true)}>
                    <Plus size={16} />
                    Add your first job
                  </Button>
                )
              }
            >
              {jobs.length
                ? 'Try a different filter or search term.'
                : 'Add a job link or paste a description. We’ll help you turn your experience into a thoughtful application.'}
            </Empty>
          )}
        </section>

        {/* Context Rail */}
        <aside className="context-rail">
          {data?.profile && (
            <div className="profile-summary">
              <div className="profile-top">
                <span className="avatar large">
                  {data.profile.name
                    .split(' ')
                    .map((s) => s[0])
                    .join('')
                    .toUpperCase()}
                </span>
                <span className="tag">Master profile</span>
              </div>
              <h2>{data.profile.name}</h2>
              <p>{data.profile.headline.split('|')[0].trim()}</p>
              <div className="skill-pills">
                <span>React</span>
                <span>Next.js</span>
                <span>TypeScript</span>
              </div>
              <div className="source-ready">
                <CheckCircle2 size={16} />
                <span>
                  CV imported <small>Source evidence ready</small>
                </span>
              </div>
              <Link to="/profile" className="text-button">
                View your profile <ArrowRight size={15} />
              </Link>
            </div>
          )}

          {data && (
            <div className="readiness">
              <h2>
                {jobs.length > 0 || (data.search_results?.items?.length ?? 0) > 0
                  ? 'Workspace readiness'
                  : 'Ready for your first search'}
              </h2>
              {[
                {
                  done: true,
                  title: 'Master CV imported',
                  sub: 'Your experience is the source of truth.',
                  path: '/profile',
                },
                {
                  done: data.preferences.confirmed,
                  title: 'Set search preferences',
                  sub: 'Titles, locations, and deal-breakers.',
                  path: '/preferences',
                },
                {
                  done:
                    data.connections.search_provider === 'free'
                      ? data.connections.free_search_ready
                      : data.connections.search_provider === 'serper'
                      ? Boolean(data.connections.serper)
                      : data.connections.brave,
                  title:
                    data.connections.search_provider === 'free'
                      ? 'LinkedIn & feed search ready'
                      : data.connections.search_provider === 'serper'
                      ? 'Google Jobs search ready'
                      : 'Connect Brave search',
                  sub:
                    data.connections.search_provider === 'free'
                      ? 'Direct LinkedIn Jobs & tech feeds active.'
                      : data.connections.search_provider === 'serper'
                      ? 'Google Jobs search active.'
                      : 'Find opportunities across the web.',
                  path: '/settings/search',
                },
                {
                  done: data.connections.connected,
                  title: 'Connect AI tailoring',
                  sub: data.connections.connected
                    ? `Active: ${data.connections.provider}`
                    : 'Use free models via OpenRouter or OpenCode.',
                  path: '/settings/ai',
                },
              ].map((x) => (
                <Link
                  key={x.title}
                  to={x.path}
                  style={{ textDecoration: 'none', color: 'inherit', display: 'flex', width: '100%' }}
                >
                  <button type="button" style={{ width: '100%' }}>
                    {x.done ? <CheckCircle2 size={18} /> : <Circle size={18} />}
                    <span>
                      {x.title}
                      <small>{x.sub}</small>
                    </span>
                    <ChevronRight size={14} />
                  </button>
                </Link>
              ))}
            </div>
          )}

          <div className="coverage-note">
            <CircleHelp size={18} />
            <h3>Aim for 95%. Stay authentic.</h3>
            <p>Coverage shows how your CV addresses the job. Real experience always comes first.</p>
          </div>
        </aside>
      </div>
    </>
  )
}
