import { STATE_LABELS } from '../lib/formatters'

export interface BadgeProps {
  state: string
  className?: string
}

export function Badge({ state, className = '' }: BadgeProps) {
  const label = STATE_LABELS[state] || state
  const badgeClass = ['badge', state, className].filter(Boolean).join(' ')

  return (
    <span className={badgeClass}>
      <span aria-hidden="true" />
      {label}
    </span>
  )
}
