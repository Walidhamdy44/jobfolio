import { NavLink, Outlet, useOutletContext } from 'react-router-dom'
import { Sparkles, Search } from 'lucide-react'

export function SettingsLayout() {
  const context = useOutletContext()

  return (
    <div>
      <div className="page-heading">
        <div>
          <h1>Give your agent its tools.</h1>
          <p>
            100% free operation: Discover jobs from public feeds and use free AI models. Offline
            manual entry always works.
          </p>
        </div>
      </div>

      <div className="filter-tabs" style={{ marginBottom: '24px' }}>
        <NavLink
          to="/settings/ai"
          className={({ isActive }) => (isActive ? 'selected' : '')}
          style={{ textDecoration: 'none' }}
        >
          <Sparkles size={15} />
          AI Connections & Models
        </NavLink>
        <NavLink
          to="/settings/search"
          className={({ isActive }) => (isActive ? 'selected' : '')}
          style={{ textDecoration: 'none' }}
        >
          <Search size={15} />
          Job Search Sources
        </NavLink>
      </div>

      <Outlet context={context} />
    </div>
  )
}
