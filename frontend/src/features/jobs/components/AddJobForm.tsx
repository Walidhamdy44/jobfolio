import React, { useState } from 'react'
import { X, Link as LinkIcon, FileText, ArrowRight } from 'lucide-react'
import { Button } from '../../../shared/ui/Button'
import { Field } from '../../../shared/ui/Field'

export interface AddJobFormProps {
  busy?: boolean
  onClose?: () => void
  onSave: (data: { url: string; title: string; company: string; location: string; description: string }) => void
  onImport: (url: string) => void
}

export function AddJobForm({ busy = false, onClose, onSave, onImport }: AddJobFormProps) {
  const [mode, setMode] = useState<'link' | 'paste'>('link')
  const [url, setUrl] = useState('')
  const [title, setTitle] = useState('')
  const [company, setCompany] = useState('')
  const [location, setLocation] = useState('')
  const [description, setDescription] = useState('')

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (mode === 'link') {
      onImport(url)
    } else {
      onSave({ url, title, company, location, description })
    }
  }

  return (
    <section className="editor-panel add-panel" aria-label="Add a job opportunity">
      <div className="section-title">
        <h2>Add an opportunity</h2>
        {onClose && (
          <button type="button" className="icon-button" onClick={onClose} aria-label="Close add job panel">
            <X size={19} />
          </button>
        )}
      </div>

      <div className="filter-tabs" aria-label="Add job method">
        <button
          type="button"
          className={mode === 'link' ? 'selected' : ''}
          onClick={() => setMode('link')}
        >
          <LinkIcon size={15} />
          Import a link
        </button>
        <button
          type="button"
          className={mode === 'paste' ? 'selected' : ''}
          onClick={() => setMode('paste')}
        >
          <FileText size={15} />
          Paste a description
        </button>
      </div>

      <form onSubmit={handleSubmit}>
        <Field label={mode === 'link' ? 'Employer job posting URL' : 'Job URL (optional)'} required={mode === 'link'}>
          <input
            type="url"
            placeholder="https://job-boards.greenhouse.io/company/jobs/…"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            required={mode === 'link'}
          />
        </Field>

        {mode === 'paste' && (
          <>
            <div className="form-grid">
              <Field label="Job title" required>
                <input
                  required
                  minLength={2}
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  placeholder="Frontend Engineer"
                />
              </Field>
              <Field label="Company" required>
                <input
                  required
                  minLength={2}
                  value={company}
                  onChange={(e) => setCompany(e.target.value)}
                  placeholder="Company name"
                />
              </Field>
            </div>
            <Field label="Location">
              <input
                value={location}
                onChange={(e) => setLocation(e.target.value)}
                placeholder="Remote, Cairo, or as listed"
              />
            </Field>
            <Field
              label="Full job description"
              hint="Include responsibilities, required skills, and preferred qualifications."
              required
            >
              <textarea
                required
                minLength={50}
                rows={8}
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="Paste the complete job description…"
              />
            </Field>
          </>
        )}

        <div className="form-actions">
          <span className="muted">No application is sent when you add a job.</span>
          <Button kind="primary" type="submit" disabled={busy} loading={busy}>
            {mode === 'link' ? 'Import posting' : 'Save opportunity'}
            <ArrowRight size={15} />
          </Button>
        </div>
      </form>
    </section>
  )
}
