import type { ReactNode } from 'react'
import { BriefcaseBusiness, FileText } from 'lucide-react'

export interface EmptyProps {
  title: string
  children: ReactNode
  action?: ReactNode
  icon?: 'jobs' | 'cv' | string
}

export function Empty({ title, children, action, icon = 'jobs' }: EmptyProps) {
  return (
    <div className="empty">
      <div className="empty-symbol" aria-hidden="true">
        {icon === 'jobs' ? <BriefcaseBusiness size={31} /> : <FileText size={31} />}
      </div>
      <h2>{title}</h2>
      <p>{children}</p>
      {action}
    </div>
  )
}
