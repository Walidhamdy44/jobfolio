import { Link } from 'react-router-dom'
import { BriefcaseBusiness, ArrowLeft } from 'lucide-react'

export function NotFoundPage() {
  return (
    <div className="empty" style={{ margin: '60px auto', maxWidth: '500px' }}>
      <div className="empty-symbol">
        <BriefcaseBusiness size={32} />
      </div>
      <h2>Page not found</h2>
      <p>The page you requested doesn't exist or has moved.</p>
      <Link to="/opportunities" className="button primary">
        <ArrowLeft size={16} />
        Go to saved opportunities
      </Link>
    </div>
  )
}
