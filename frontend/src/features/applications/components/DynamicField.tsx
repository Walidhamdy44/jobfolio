import { FileText } from 'lucide-react'
import type { FormField } from '../../../types'
import { Field } from '../../../shared/ui/Field'

export interface DynamicFieldProps {
  field: FormField
  value: string
  onChange: (val: string) => void
  disabled?: boolean
}

export function DynamicField({ field: f, value, onChange, disabled = false }: DynamicFieldProps) {
  // File upload note
  if (f.type === 'file') {
    const isCv = /resume|cv\b/i.test(f.label)
    return (
      <div className="upload-note" role="note">
        <FileText size={18} aria-hidden="true" />
        <div>
          <strong>{f.label}</strong>
          <p>
            {isCv
              ? 'Your approved PDF CV will be attached automatically by the agent.'
              : 'Additional employer uploads need manual completion.'}
          </p>
        </div>
      </div>
    )
  }

  // Radio field
  if (f.type === 'radio' && f.options && f.options.length > 0) {
    return (
      <fieldset className="field" style={{ border: 0, padding: 0, margin: '0 0 20px 0' }}>
        <legend style={{ fontSize: '12px', fontWeight: 650, color: '#3f5546', marginBottom: '8px' }}>
          {f.label}
          {f.required && <span aria-hidden="true" style={{ color: 'var(--color-error)' }}> *</span>}
        </legend>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
          {f.options.map((opt) => (
            <label key={opt.value} className="check-field" style={{ margin: 0 }}>
              <input
                type="radio"
                name={f.key}
                value={opt.value}
                checked={value === opt.value}
                disabled={disabled}
                onChange={(e) => onChange(e.target.value)}
              />
              <span>{opt.label || opt.value}</span>
            </label>
          ))}
        </div>
      </fieldset>
    )
  }

  // Checkbox field
  if (f.type === 'checkbox') {
    return (
      <label className="check-field">
        <input
          type="checkbox"
          disabled={disabled}
          checked={value === 'true'}
          onChange={(e) => onChange(e.target.checked ? 'true' : 'false')}
        />
        <span>
          {f.label}
          {f.required && ' *'}
        </span>
      </label>
    )
  }

  // Select field
  if (f.type === 'select') {
    return (
      <Field label={f.label} required={f.required}>
        <select
          disabled={disabled}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          aria-label={f.label}
        >
          <option value="">Choose an answer</option>
          {f.options?.filter((o) => o.value).map((o) => (
            <option key={o.value} value={o.value}>
              {o.label || o.value}
            </option>
          ))}
        </select>
      </Field>
    )
  }

  // Textarea field
  if (f.type === 'textarea') {
    return (
      <Field label={f.label} required={f.required}>
        <textarea
          disabled={disabled}
          rows={4}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder="Enter your answer"
        />
      </Field>
    )
  }

  // Native input types (text, email, tel, url, number, date)
  const inputType = ['email', 'tel', 'url', 'number', 'date'].includes(f.type) ? f.type : 'text'
  return (
    <Field label={f.label} required={f.required}>
      <input
        type={inputType}
        disabled={disabled}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder="Enter your answer"
      />
    </Field>
  )
}
