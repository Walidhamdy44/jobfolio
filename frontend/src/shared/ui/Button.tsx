import { forwardRef, type ButtonHTMLAttributes, type ReactNode } from 'react'
import { LoaderCircle } from 'lucide-react'

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  children: ReactNode
  kind?: 'primary' | 'submit-button' | 'outline' | 'text' | 'danger' | ''
  loading?: boolean
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(function Button(
  { children, kind = '', loading = false, disabled = false, className = '', type = 'button', ...props },
  ref
) {
  const buttonClass = ['button', kind, className].filter(Boolean).join(' ')

  return (
    <button
      ref={ref}
      type={type}
      className={buttonClass}
      disabled={disabled || loading}
      {...props}
    >
      {loading ? <LoaderCircle className="spin" size={15} /> : null}
      {children}
    </button>
  )
})
