import { useState, useEffect, Fragment } from 'react'
import { Outlet, NavLink, useLocation, Link } from 'react-router-dom'
import {
  BriefcaseBusiness,
  ChevronRight,
  ShieldCheck,
  RefreshCw,
  X,
  LoaderCircle,
  Check,
} from 'lucide-react'
import { MAIN_NAV } from '../navigation'
import { useBootstrapQuery } from '../../features/workspace/queries'
import { Notice } from '../../shared/ui/Notice'

export function AppLayout() {
  const location = useLocation()
  const { data, isLoading, error, refetch } = useBootstrapQuery()

  const [dismissedRun, setDismissedRun] = useState<string>('')
  const [toast, setToast] = useState<string>('')
  const [isManualRefreshing, setIsManualRefreshing] = useState(false)

  const handleManualRefresh = async () => {
    setIsManualRefreshing(true)
    try {
      await refetch()
    } finally {
      setIsManualRefreshing(false)
    }
  }

  useEffect(() => {
    if (toast) {
      const t = setTimeout(() => setToast(''), 5000)
      return () => clearTimeout(t)
    }
  }, [toast])

  const activeRuns = data?.runs.filter((r) => ['queued', 'running'].includes(r.state)) || []

  // Derive initials from profile name
  const profileName = data?.profile?.name || 'Walid Hamdy'
  const initials = profileName
    .split(' ')
    .filter(Boolean)
    .slice(0, 2)
    .map((s) => s[0].toUpperCase())
    .join('') || 'WH'

  // Determine current active page label for breadcrumbs
  const currentNav = MAIN_NAV.find((n) => location.pathname.startsWith(n.path))
  const isJobDetail = location.pathname.startsWith('/jobs/') && location.pathname !== '/jobs/new'

  if (isLoading && !data) {
    return (
      <main className="loading-page">
        <BriefcaseBusiness size={30} aria-hidden="true" />
        <h1>Opening your workspace</h1>
        <p>Loading your profile and saved jobs…</p>
      </main>
    )
  }

  return (
    <div className="app-shell">
      <a href="#main" className="skip-link">
        Skip to content
      </a>

      {/* Sidebar Navigation */}
      <aside className="sidebar" aria-label="Main sidebar">
        <Link to="/opportunities" className="brand">
          <span className="brand-mark" aria-hidden="true">
            <BriefcaseBusiness size={22} />
          </span>
          jobfolio<span className="brand-dot">.</span>
        </Link>

        <div className="workspace-switch">
          <span className="avatar">{initials}</span>
          <div>
            Personal workspace
            <small>{profileName}</small>
          </div>
        </div>

        <nav aria-label="Main navigation">
          {MAIN_NAV.map((n) => (
            <Fragment key={n.id}>
              {n.dividerBefore && <div className="nav-divider" />}
              <NavLink
                to={n.path}
                className={({ isActive }) => (isActive ? 'active' : '')}
                aria-current={location.pathname.startsWith(n.path) ? 'page' : undefined}
              >
                <n.icon size={19} aria-hidden="true" />
                <span>{n.name}</span>
                {n.id === 'opportunities' && data?.jobs && data.jobs.length > 0 && (
                  <b>{data.jobs.length}</b>
                )}
                {n.id === 'discover' && data?.search_results?.items && data.search_results.items.length > 0 && (
                  <b>{data.search_results.items.length}</b>
                )}
              </NavLink>
            </Fragment>
          ))}
        </nav>

        <div className="sidebar-bottom">
          <ShieldCheck size={19} aria-hidden="true" />
          <div>
            You’re in control
            <small>
              Every application needs
              <br />
              your approval.
            </small>
          </div>
        </div>

        <div className="local-status">
          <span aria-hidden="true" />
          Runs on your computer
        </div>
      </aside>

      {/* Main Workspace Area */}
      <div className="workspace">
        <header className="topbar">
          <div aria-label="Breadcrumb navigation">
            <span>Workspace</span>
            <ChevronRight size={14} aria-hidden="true" />
            {currentNav && <strong>{currentNav.name}</strong>}
            {isJobDetail && (
              <>
                <ChevronRight size={14} aria-hidden="true" />
                <span>Review</span>
              </>
            )}
            {location.pathname === '/jobs/new' && (
              <>
                <ChevronRight size={14} aria-hidden="true" />
                <span>New job</span>
              </>
            )}
          </div>

          <div className="topbar-right">
            <button
              type="button"
              className="icon-button"
              title="Refresh workspace data"
              onClick={() => void handleManualRefresh()}
              aria-label="Refresh workspace data"
              disabled={isManualRefreshing}
              style={{ padding: '6px', marginRight: '4px' }}
            >
              <RefreshCw size={14} className={isManualRefreshing ? 'spin' : ''} />
            </button>
            <span className="connection-dot" aria-hidden="true" />
            <span>Local workspace</span>
            <span className="avatar light">{initials}</span>
          </div>
        </header>

        <main id="main">
          {/* Global network/loading error */}
          {error && (
            <div className="global-error" role="alert">
              <Notice kind="error">{error.message}</Notice>
            </div>
          )}

          {/* Latest failed run alert */}
          {(() => {
            const failedRun = data?.runs?.[0]
            if (
              !failedRun ||
              !['failed', 'interrupted'].includes(failedRun.state) ||
              dismissedRun === failedRun.id
            ) {
              return null
            }
            const targetJob = failedRun.target ? data?.jobs?.find((j) => j.id === failedRun.target) : undefined
            return (
              <div className="global-error" role="alert">
                <Notice kind="error">
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                    <div>
                      <strong>Operation failed</strong>
                      {targetJob ? (
                        <span>
                          {' for '}
                          <Link
                            to={`/jobs/${targetJob.id}/description`}
                            style={{ fontWeight: 700, textDecoration: 'underline' }}
                          >
                            {targetJob.title} ({targetJob.company})
                          </Link>
                        </span>
                      ) : null}
                      : {failedRun.message}
                    </div>
                    {targetJob && (
                      <Link
                        to={`/jobs/${targetJob.id}/description`}
                        style={{ fontSize: '11px', fontWeight: 600, color: 'inherit' }}
                      >
                        Review job and description →
                      </Link>
                    )}
                  </div>
                </Notice>
                <button
                  type="button"
                  className="icon-button"
                  aria-label="Dismiss operation error"
                  onClick={() => setDismissedRun(failedRun.id)}
                >
                  <X size={17} />
                </button>
              </div>
            )
          })()}

          {/* Live Agent Processing Banner */}
          {activeRuns.length > 0 && (
            <div className="run-banner-card" role="status" aria-live="polite">
              <div className="run-banner-main">
                <div className="run-spinner-wrap" aria-hidden="true">
                  <LoaderCircle className="spin" size={20} />
                </div>
                <div className="run-banner-text">
                  <div className="run-banner-title">
                    <strong>
                      {activeRuns[0].kind === 'prepare'
                        ? 'Preparing tailored CV'
                        : activeRuns[0].kind === 'search'
                        ? 'Searching job opportunities'
                        : activeRuns[0].kind === 'inspect'
                        ? 'Reading application questions'
                        : activeRuns[0].kind === 'submit'
                        ? 'Submitting approved application'
                        : activeRuns[0].kind === 'cover-letter'
                        ? 'Drafting tailored cover letter'
                        : 'Importing job posting'}
                      …
                    </strong>
                    <span className="live-pill">
                      <span className="pulse-dot" aria-hidden="true" />
                      Live Agent Processing
                    </span>
                  </div>
                  <p className="run-step-text">{activeRuns[0].message || 'Agent active…'}</p>
                </div>
                <span className="run-banner-aside">Background operation</span>
              </div>
            </div>
          )}

          <Outlet context={{ data, setToast }} />
        </main>

        <footer className="footer">
          <span>Built around your experience.</span>
          <span>Local storage · Your approval, every time</span>
        </footer>
      </div>

      {/* Global Toast */}
      {toast && (
        <div className="toast" role="status" aria-live="polite">
          <Check size={18} aria-hidden="true" />
          <span>{toast}</span>
          <button
            type="button"
            className="icon-button"
            aria-label="Dismiss message"
            onClick={() => setToast('')}
          >
            <X size={15} />
          </button>
        </div>
      )}
    </div>
  )
}
