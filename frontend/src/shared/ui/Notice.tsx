import type { ReactNode } from 'react'
import { CircleAlert, CheckCircle2, AlertTriangle, Info } from 'lucide-react'

export interface NoticeProps {
  children: ReactNode
  kind?: 'info' | 'warning' | 'error' | 'success'
  className?: string
  role?: string
}

export function Notice({ children, kind = 'info', className = '', role }: NoticeProps) {
  const Icon = kind === 'error'
    ? CircleAlert
    : kind === 'warning'
    ? AlertTriangle
    : kind === 'success'
    ? CheckCircle2
    : Info

  return (
    <div className={`notice ${kind} ${className}`} role={role || (kind === 'error' ? 'alert' : 'status')}>
      <Icon size={17} aria-hidden="true" />
      <div>{children}</div>
    </div>
  )
}
