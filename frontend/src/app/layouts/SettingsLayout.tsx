import { NavLink, Outlet, useOutletContext } from 'react-router-dom'
import { Sparkles, Search } from 'lucide-react'

export function SettingsLayout() {
  const context = useOutletContext()

  return (
    <div className="settings-layout">
      <header className="settings-intro">
        <h1>Give your agent its tools.</h1>
        <p>
          100% free operation: Discover jobs from public feeds and use free AI models. Offline
          manual entry always works.
        </p>
      </header>

      <nav className="settings-tabs" aria-label="Settings sections">
        <NavLink
          to="/settings/ai"
          end
          className="settings-tab"
        >
          <Sparkles size={15} />
          AI Connections & Models
        </NavLink>
        <NavLink
          to="/settings/search"
          className="settings-tab"
        >
          <Search size={15} />
          Job Search Sources
        </NavLink>
      </nav>

      <Outlet context={context} />
    </div>
  )
}
