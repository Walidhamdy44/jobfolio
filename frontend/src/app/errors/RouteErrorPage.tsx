import { useRouteError, isRouteErrorResponse, Link } from 'react-router-dom'
import { AlertTriangle, ArrowLeft } from 'lucide-react'

export function RouteErrorPage() {
  const error = useRouteError()
  let title = 'Something went wrong'
  let message = 'An unexpected error occurred while loading this page.'

  if (isRouteErrorResponse(error)) {
    title = `${error.status} ${error.statusText}`
    message = (error.data as { message?: string })?.message || message
  } else if (error instanceof Error) {
    message = error.message
  }

  return (
    <div className="empty" style={{ margin: '40px auto', maxWidth: '600px' }}>
      <div className="empty-symbol" style={{ color: 'var(--color-error)' }}>
        <AlertTriangle size={32} />
      </div>
      <h2>{title}</h2>
      <p>{message}</p>
      <Link to="/opportunities" className="button primary">
        <ArrowLeft size={16} />
        Back to opportunities
      </Link>
    </div>
  )
}
