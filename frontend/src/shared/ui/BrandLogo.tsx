import './BrandLogo.css'

export function BrandLogo({ loading = false }: { loading?: boolean }) {
  return (
    <span className={`brand-logo-window${loading ? ' brand-logo-window--loading' : ''}`}>
      <img className="brand-logo-image" src="/jobfolio-logo.png" alt="Jobfolio" />
    </span>
  )
}
