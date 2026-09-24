import type { ReactNode } from 'react'

export interface FieldProps {
  label: string
  children: ReactNode
  hint?: string
  error?: string
  required?: boolean
  htmlFor?: string
  className?: string
}

export function Field({ label, children, hint, error, htmlFor, className = '' }: FieldProps) {
  return (
    <label className={`field ${className}`} htmlFor={htmlFor}>
      <span>{label}</span>
      {children}
      {hint && !error && <small>{hint}</small>}
      {error && <small style={{ color: 'var(--color-error)' }} role="alert">{error}</small>}
    </label>
  )
}
