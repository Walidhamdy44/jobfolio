import { useState } from 'react'
import { BriefcaseBusiness } from 'lucide-react'

type Props = {
  company?: string
  logoUrl?: string | null
}

export function CompanyLogo({ company, logoUrl }: Props) {
  const [imageFailed, setImageFailed] = useState(false)
  const label = company?.trim() || ''
  const displayName = /^(?:employer|not stated\b)/i.test(label) ? '' : label
  const parts = displayName.split(/\s+/).filter(Boolean)
  const initials = parts.length > 1
    ? parts.slice(0, 2).map((part) => part[0]).join('').toUpperCase()
    : parts[0]?.slice(0, 2).toUpperCase()

  return (
    <span
      className="company-logo"
      role="img"
      aria-label={displayName ? `${displayName} company logo` : 'Company logo unavailable'}
    >
      <span className="company-logo-fallback" aria-hidden="true">
        {initials || <BriefcaseBusiness size={17} />}
      </span>
      {logoUrl && !imageFailed && (
        <img
          src={`/api/search/company-logo?url=${encodeURIComponent(logoUrl)}`}
          alt=""
          loading="lazy"
          decoding="async"
          onError={() => setImageFailed(true)}
        />
      )}
    </span>
  )
}
