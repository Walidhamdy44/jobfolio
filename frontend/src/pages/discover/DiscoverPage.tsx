import { useEffect } from 'react'
import { useSearchParams, useOutletContext, useNavigate, Link } from 'react-router-dom'
import {
  Search,
  Plus,
  ArrowUpRight,
  ChevronLeft,
  ChevronRight,
  CheckCircle2,
} from 'lucide-react'
import { Button } from '../../shared/ui/Button'
import { Empty } from '../../shared/ui/Empty'
import { useSearchMutation } from '../../features/workspace/queries'
import { useImportJobMutation } from '../../features/jobs/queries'
import type { Bootstrap } from '../../types'

const ITEMS_PER_PAGE = 25

function formatPlatformName(platform: string, source?: string) {
  if (source && source !== 'Feed search') return source
  const map: Record<string, string> = {
    weworkremotely: 'WeWorkRemotely',
    jobicy: 'Jobicy',
    remotive: 'Remotive',
    arbeitnow: 'Arbeitnow',
    linkedin: 'LinkedIn',
    google: 'Google Jobs',
    greenhouse: 'Greenhouse',
    lever: 'Lever',
    manual: 'Web posting',
    web: 'Brave Search',
    pasted: 'Pasted',
  }
  return map[platform.toLowerCase()] || platform
}

export function DiscoverPage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const navigate = useNavigate()
  const { data, setToast } = useOutletContext<{
    data?: Bootstrap
    setToast: (msg: string) => void
  }>()

  const searchMutation = useSearchMutation()
  const importJobMutation = useImportJobMutation()

  const query = searchParams.get('q') || ''
  const trimmedQuery = query.trim().toLowerCase()

  const setQuery = (newQuery: string) => {
    setSearchParams((prev) => {
      const p = new URLSearchParams(prev)
      if (newQuery) p.set('q', newQuery)
      else p.delete('q')
      p.set('page', '1')
      return p
    })
  }

  const setPage = (newPage: number) => {
    setSearchParams((prev) => {
      const p = new URLSearchParams(prev)
      p.set('page', String(newPage))
      return p
    })
  }

  const allItems = data?.search_results?.items || []
  const filteredItems = allItems.filter((hit) => {
    if (!trimmedQuery) return true
    return (
      hit.title.toLowerCase().includes(trimmedQuery) ||
      hit.snippet.toLowerCase().includes(trimmedQuery)
    )
  })

  const totalPages = Math.max(1, Math.ceil(filteredItems.length / ITEMS_PER_PAGE))
  const rawPage = parseInt(searchParams.get('page') || '1', 10)
  const validPage = Number.isFinite(rawPage) && rawPage >= 1 ? rawPage : 1
  const currentPage = Math.min(validPage, totalPages)

  useEffect(() => {
    const pageInParam = searchParams.get('page')
    if (pageInParam !== null && (String(currentPage) !== pageInParam || !Number.isFinite(rawPage) || rawPage < 1)) {
      setSearchParams(
        (prev) => {
          const p = new URLSearchParams(prev)
          p.set('page', String(currentPage))
          return p
        },
        { replace: true }
      )
    }
  }, [currentPage, rawPage, searchParams, setSearchParams])

  const paginatedItems = filteredItems.slice(
    (currentPage - 1) * ITEMS_PER_PAGE,
    currentPage * ITEMS_PER_PAGE
  )

  // Map of saved job URLs to check if already imported
  const savedUrls = new Set(data?.jobs?.map((j) => j.url).filter(Boolean))

  const handleStartSearch = async () => {
    try {
      await searchMutation.mutateAsync()
      setToast('Job search started across free public feeds.')
    } catch (e) {
      setToast((e as Error).message)
    }
  }

  const handleImport = async (url: string) => {
    try {
      const res = await importJobMutation.mutateAsync({ url })
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

  const isSearching =
    searchMutation.isPending ||
    data?.runs?.some((r) => r.kind === 'search' && ['queued', 'running'].includes(r.state))

  return (
    <div>
      <div className="page-heading">
        <div>
          <h1>Discover Opportunities</h1>
          <p>
            Find roles matching your skills from LinkedIn, Google Jobs, and curated feeds.
            Import them to tailor a CV.
          </p>
        </div>
        <Button
          kind="primary"
          disabled={isSearching}
          loading={isSearching}
          onClick={() => void handleStartSearch()}
        >
          <Search size={16} />
          {isSearching ? 'Searching opportunities…' : 'Run new search'}
        </Button>
      </div>

      <div className="search-launch" style={{ marginBottom: '24px' }}>
        <div className="search-launch-icon">
          <Search size={23} />
        </div>
        <div>
          <h2>
            {data?.connections.search_provider === 'serper'
              ? 'Google Jobs search active'
              : data?.connections.search_provider === 'brave'
              ? 'Brave web search active'
              : 'LinkedIn & curated feed search active'}
          </h2>
          <p>
            Target titles: {data?.preferences.titles.join(' · ') || 'Frontend Engineer'}
          </p>
          <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap', marginTop: '6px', fontSize: '11px', color: '#53644d' }}>
            <span>📍 {[data?.preferences.location, data?.preferences.country].filter(Boolean).join(', ') || 'Any location'}</span>
            <span>·</span>
            <span>🏢 {data?.preferences.workplace_type && data.preferences.workplace_type !== 'any' ? (data.preferences.workplace_type === 'on_site' ? 'On-site' : data.preferences.workplace_type.charAt(0).toUpperCase() + data.preferences.workplace_type.slice(1)) : (data?.preferences.remote_only ? 'Remote' : 'Any workplace')}</span>
            <span>·</span>
            <span>📅 {data?.preferences.date_posted === 'past_24h' ? 'Past 24h' : data?.preferences.date_posted === 'past_week' ? 'Past week' : data?.preferences.date_posted === 'past_month' ? 'Past month' : 'Any time'}</span>
            <span>·</span>
            <span>🎯 {data?.preferences.experience_level === 'senior' ? 'Senior' : data?.preferences.experience_level === 'mid' ? 'Mid-level' : data?.preferences.experience_level === 'entry' ? 'Entry level' : 'All levels'}</span>
            <span>·</span>
            <span>⏱️ {data?.preferences.job_type === 'full_time' ? 'Full-time' : data?.preferences.job_type === 'contract' ? 'Contract' : data?.preferences.job_type === 'part_time' ? 'Part-time' : 'All types'}</span>
          </div>
        </div>
        <Link to="/preferences" className="text-button" style={{ marginLeft: 'auto' }}>
          Adjust search criteria
        </Link>
      </div>

      <section className="search-results">
        <div className="section-title">
          <div>
            <h2>
              Discovered results <span>{filteredItems.length}</span>
            </h2>
            <small>
              Relevance matching is calculated against your target roles and technical skills.
            </small>
          </div>
          <div className="inline-search">
            <Search size={15} />
            <input
              placeholder="Filter results…"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              aria-label="Filter discovered jobs"
            />
          </div>
        </div>

        {paginatedItems.length > 0 ? (
          <div>
            {paginatedItems.map((hit) => {
              const isSaved = savedUrls.has(hit.url)
              const savedJob = isSaved ? data?.jobs.find((j) => j.url === hit.url) : null

              return (
                <div className="result-row" key={hit.url}>
                  <div className="result-info">
                    <div className="result-header">
                      <a href={hit.url} target="_blank" rel="noreferrer">
                        {hit.title}
                        <ArrowUpRight size={14} />
                      </a>
                      {hit.score !== undefined && (
                        <span className="score-pill" title="Keyword and role alignment score">
                          {hit.score}% Match
                        </span>
                      )}
                      <span className="platform-tag">
                        {formatPlatformName(hit.platform, hit.source)}
                      </span>
                      {hit.posted_at && (
                        <time className="small" dateTime={hit.posted_at}>
                          Posted {new Date(hit.posted_at).toLocaleDateString(undefined, {
                            day: 'numeric', month: 'short', year: 'numeric', timeZone: 'UTC',
                          })}
                        </time>
                      )}
                      {isSaved && (
                        <span
                          style={{
                            fontSize: '9.5px',
                            color: 'var(--color-action)',
                            display: 'inline-flex',
                            alignItems: 'center',
                            gap: '4px',
                            fontWeight: 650,
                          }}
                        >
                          <CheckCircle2 size={12} />
                          Already saved
                        </span>
                      )}
                    </div>
                    <p>{hit.snippet}</p>
                  </div>

                  {isSaved && savedJob ? (
                    <Link to={`/jobs/${savedJob.id}/description`} className="button">
                      Open job
                    </Link>
                  ) : (
                    <Button
                      disabled={importJobMutation.isPending}
                      onClick={() => void handleImport(hit.url)}
                    >
                      <Plus size={14} />
                      Import
                    </Button>
                  )}
                </div>
              )
            })}

            {/* Pagination Controls */}
            {totalPages > 1 && (
              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  paddingTop: '20px',
                  marginTop: '10px',
                  borderTop: '1px solid var(--color-border)',
                }}
              >
                <span className="small">
                  Showing {(currentPage - 1) * ITEMS_PER_PAGE + 1}–
                  {Math.min(currentPage * ITEMS_PER_PAGE, filteredItems.length)} of {filteredItems.length}
                </span>

                <div className="button-group">
                  <Button disabled={currentPage <= 1} onClick={() => setPage(currentPage - 1)}>
                    <ChevronLeft size={14} />
                    Previous
                  </Button>
                  <span
                    style={{
                      display: 'inline-flex',
                      alignItems: 'center',
                      fontSize: '11px',
                      fontWeight: 600,
                      padding: '0 8px',
                    }}
                  >
                    Page {currentPage} of {totalPages}
                  </span>
                  <Button disabled={currentPage >= totalPages} onClick={() => setPage(currentPage + 1)}>
                    Next
                    <ChevronRight size={14} />
                  </Button>
                </div>
              </div>
            )}
          </div>
        ) : allItems.length > 0 ? (
          <Empty
            title="No results match your filter"
            icon="jobs"
            action={
              <Button onClick={() => setQuery('')}>
                Clear search filter
              </Button>
            }
          >
            No discovered opportunities matched &ldquo;{query.trim()}&rdquo;. Try clearing or adjusting your search term.
          </Empty>
        ) : (
          <Empty
            title="No discovered jobs yet"
            icon="jobs"
            action={
              <Button
                kind="primary"
                disabled={isSearching}
                onClick={() => void handleStartSearch()}
              >
                <Search size={15} />
                Find opportunities now
              </Button>
            }
          >
            Click &ldquo;Find opportunities now&rdquo; to query free tech feeds for roles matching your preferences.
          </Empty>
        )}
      </section>
    </div>
  )
}
