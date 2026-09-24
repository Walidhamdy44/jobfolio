import React, { useState, useEffect } from 'react'
import { Link, useOutletContext, useBlocker } from 'react-router-dom'
import {
  Sparkles,
  ExternalLink,
  Plus,
  Trash2,
  RotateCcw,
  Check,
  FileText,
  LoaderCircle,
  ArrowRight,
} from 'lucide-react'
import { Button } from '../../shared/ui/Button'
import { Field } from '../../shared/ui/Field'
import { Notice } from '../../shared/ui/Notice'
import {
  useSaveProfileMutation,
  useStructureProfileMutation,
} from '../../features/workspace/queries'
import type { Bootstrap, Profile } from '../../types'

export function ProfilePage() {
  const { data, setToast } = useOutletContext<{
    data?: Bootstrap
    setToast: (msg: string) => void
  }>()

  const initialProfile = data?.profile

  const [p, setP] = useState<Profile | null>(initialProfile || null)
  const [confirmed, setConfirmed] = useState(false)
  const [structuredNotice, setStructuredNotice] = useState('')
  const [structureError, setStructureError] = useState('')

  const saveProfileMutation = useSaveProfileMutation()
  const structureMutation = useStructureProfileMutation()

  useEffect(() => {
    if (initialProfile && !p) {
      setP(initialProfile)
    }
  }, [initialProfile])

  const isModified = Boolean(p && initialProfile && JSON.stringify(p) !== JSON.stringify(initialProfile))

  // Block in-app navigation when there are unsaved changes
  const blocker = useBlocker(
    ({ currentLocation, nextLocation }) =>
      isModified && currentLocation.pathname !== nextLocation.pathname
  )

  // Warn on browser reload or close when modified
  useEffect(() => {
    const handleBeforeUnload = (e: BeforeUnloadEvent) => {
      if (isModified) {
        e.preventDefault()
      }
    }
    window.addEventListener('beforeunload', handleBeforeUnload)
    return () => window.removeEventListener('beforeunload', handleBeforeUnload)
  }, [isModified])

  if (!p) {
    return <p className="muted">Loading profile…</p>
  }

  const update = (field: string, value: unknown) => {
    setP((prev) => (prev ? { ...prev, [field]: value } : prev))
    setConfirmed(false)
  }

  const updateItem = (si: number, ii: number, text: string) => {
    setP((prev) => {
      if (!prev) return prev
      const sections = structuredClone(prev.sections)
      sections[si].items[ii].text = text
      return { ...prev, sections }
    })
    setConfirmed(false)
  }

  const removeItem = (si: number, ii: number) => {
    setP((prev) => {
      if (!prev) return prev
      const sections = structuredClone(prev.sections)
      sections[si].items.splice(ii, 1)
      return { ...prev, sections }
    })
    setConfirmed(false)
  }

  const addItem = (si: number) => {
    setP((prev) => {
      if (!prev) return prev
      const sections = structuredClone(prev.sections)
      sections[si].items.push({
        id: 'e' + Date.now() + '_' + Math.random().toString(36).slice(2, 6),
        text: '',
      })
      return { ...prev, sections }
    })
    setConfirmed(false)
  }

  const resetToInitial = () => {
    if (!initialProfile) return
    setP(initialProfile)
    setConfirmed(false)
    setStructuredNotice('')
    setStructureError('')
  }

  const handleStructure = async (mode: 'ai' | 'local') => {
    setStructureError('')
    setStructuredNotice('')
    try {
      const res = await structureMutation.mutateAsync({ mode })
      setP(res.profile)
      setConfirmed(false)
      if (mode === 'ai') {
        setStructuredNotice(
          'Master CV reviewed & structured by AI! Fragmented lines were merged into complete statements. Please review each section below, edit or delete any items, check confirmation, and save.'
        )
      } else {
        setStructuredNotice(
          'Master CV structured with smart local heuristics. Fragmented lines were merged into complete statements. Please review and confirm below.'
        )
      }
    } catch (e) {
      setStructureError((e as Error).message)
    }
  }

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!p) return
    try {
      const { source_file: _s, revision: _r, ...body } = p
      await saveProfileMutation.mutateAsync(body as Profile)
      setToast('Master profile updated. Fresh CV packages will reflect these changes.')
      setConfirmed(false)
    } catch (err) {
      setToast((err as Error).message)
    }
  }

  const isAiConnected = Boolean(data?.connections?.connected)
  const isBusy = saveProfileMutation.isPending || structureMutation.isPending

  return (
    <>
      <div className="page-heading">
        <div>
          <h1>The experience behind every application.</h1>
          <p>Your master profile. Every tailored CV starts here.</p>
        </div>
        <a className="button" href="/api/master-cv" target="_blank" rel="noreferrer">
          <ExternalLink size={15} />
          Original CV
        </a>
      </div>

      {/* AI CV Structuring Proposal Card */}
      <section className="editor-panel profile-ai-card" aria-label="Review and structure CV">
        <div className="profile-ai-header">
          <div className="profile-ai-title">
            <Sparkles size={22} className="sparkle-accent" aria-hidden="true" />
            <div>
              <h2>Review & Structure with AI</h2>
              <p>
                Don&apos;t settle for raw, line-by-line fragments. Use a free AI model to analyze your
                master CV ({p.source_file || 'CV'}) and synthesize complete, professional entries before
                saving.
              </p>
            </div>
          </div>
          <span className={`tag ${isAiConnected ? 'connected' : ''}`}>
            {isAiConnected ? `AI key saved (${data?.connections?.provider}; not verified)` : 'Key needed'}
          </span>
        </div>

        <div className="profile-ai-model-info">
          <span>
            Active Model: <strong>{data?.connections?.model || 'openrouter/free'}</strong>
          </span>
          {!isAiConnected && (
            <Link to="/settings/ai" className="text-button">
              Connect a free AI key in Connections <ArrowRight size={13} />
            </Link>
          )}
        </div>

        <div className="profile-ai-actions">
          <Button
            kind="primary"
            disabled={isBusy || !isAiConnected}
            loading={structureMutation.isPending && structureMutation.variables?.mode === 'ai'}
            onClick={() => void handleStructure('ai')}
          >
            <Sparkles size={16} />
            Review & Structure with AI
          </Button>
          <Button
            disabled={isBusy}
            loading={structureMutation.isPending && structureMutation.variables?.mode === 'local'}
            onClick={() => void handleStructure('local')}
          >
            <FileText size={16} />
            Clean up locally (offline)
          </Button>
        </div>

        {structureMutation.isPending && (
          <div className="run-banner" style={{ marginTop: '16px' }} role="status">
            <LoaderCircle className="spin" size={16} />
            <strong>Analyzing your CV and merging fragmented lines…</strong>
            <span>This takes just a few seconds.</span>
          </div>
        )}

        {structureError && (
          <Notice kind="error">
            {structureError}
            {!isAiConnected && <Link to="/settings/ai" className="button" style={{ marginLeft: '12px' }}>Open Connections</Link>}
          </Notice>
        )}

        {structuredNotice && <Notice kind="success">{structuredNotice}</Notice>}
      </section>

      {/* Main Profile Form */}
      <form className="profile-editor" onSubmit={handleSave}>
        <section className="editor-panel">
          <h2>Personal details</h2>
          <div className="form-grid">
            {(['name', 'headline', 'email', 'phone', 'location'] as const).map((k) => (
              <Field key={k} label={k.charAt(0).toUpperCase() + k.slice(1)} required={['name', 'headline'].includes(k)}>
                <input
                  value={p[k]}
                  required={['name', 'headline'].includes(k)}
                  onChange={(e) => update(k, e.target.value)}
                />
              </Field>
            ))}
            <Field label="Portfolio and profile links" hint="One URL per line">
              <textarea
                rows={3}
                value={p.links.join('\n')}
                onChange={(e) => update('links', e.target.value.split('\n').filter(Boolean))}
              />
            </Field>
          </div>
        </section>

        {p.sections.map((s, si) => (
          <section className="editor-panel profile-section-panel" key={si}>
            <div className="section-title">
              <div className="section-heading-row">
                <h2>{s.title}</h2>
                <span className="entry-count">
                  {s.items.length} {s.items.length === 1 ? 'entry' : 'entries'}
                </span>
              </div>
              <button type="button" className="text-button" onClick={() => addItem(si)}>
                <Plus size={15} />
                Add evidence
              </button>
            </div>

            {s.items.length === 0 ? (
              <p className="muted small">No entries in this section. Click &ldquo;Add evidence&rdquo; to add one.</p>
            ) : (
              s.items.map((item, ii) => (
                <div className="profile-item-row" key={item.id}>
                  <div className="profile-item-field">
                    <Field label={s.items.length === 1 ? s.title : `Entry ${ii + 1}`} required>
                      <textarea
                        rows={Math.max(2, Math.min(6, Math.ceil(item.text.length / 90)))}
                        required
                        value={item.text}
                        onChange={(e) => updateItem(si, ii, e.target.value)}
                        placeholder="Describe your role, achievement, or skill group…"
                      />
                    </Field>
                  </div>
                  <button
                    type="button"
                    className="icon-button item-delete-btn"
                    title="Delete this entry"
                    aria-label={`Delete entry ${ii + 1}`}
                    onClick={() => removeItem(si, ii)}
                  >
                    <Trash2 size={15} />
                  </button>
                </div>
              ))
            )}
          </section>
        ))}

        <div className="sticky-save">
          <label className="check-field">
            <input
              type="checkbox"
              required
              checked={confirmed}
              onChange={(e) => setConfirmed(e.target.checked)}
            />
            <span>I confirm these details accurately reflect my experience.</span>
          </label>

          <div className="button-group">
            {isModified && (
              <Button disabled={isBusy} onClick={resetToInitial}>
                <RotateCcw size={15} />
                Revert
              </Button>
            )}
            <Button
              type="submit"
              kind="primary"
              disabled={isBusy || !confirmed}
              loading={saveProfileMutation.isPending}
            >
              Save master profile
              <Check size={15} />
            </Button>
          </div>
        </div>
      </form>

      {blocker.state === 'blocked' && (
        <div
          role="dialog"
          aria-modal="true"
          aria-labelledby="unsaved-modal-title"
          style={{
            position: 'fixed',
            inset: 0,
            backgroundColor: 'rgba(0, 0, 0, 0.45)',
            display: 'grid',
            placeItems: 'center',
            zIndex: 1000,
            padding: '20px',
          }}
        >
          <div
            style={{
              background: '#fff',
              borderRadius: '10px',
              padding: '28px',
              maxWidth: '480px',
              width: '100%',
              boxShadow: '0 10px 30px rgba(0,0,0,0.18)',
            }}
          >
            <h3 id="unsaved-modal-title" style={{ fontSize: '17px', marginBottom: '10px' }}>
              Discard unsaved profile changes?
            </h3>
            <p style={{ fontSize: '13px', color: 'var(--muted, #55695c)', lineHeight: 1.6, marginBottom: '22px' }}>
              You have edited your profile without saving. If you leave now, your changes will be discarded.
            </p>
            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '12px' }}>
              <Button
                type="button"
                onClick={() => blocker.reset()}
              >
                Stay and keep editing
              </Button>
              <Button
                type="button"
                kind="primary"
                style={{ backgroundColor: '#8c453b', borderColor: '#8c453b' }}
                onClick={() => blocker.proceed()}
              >
                Discard changes
              </Button>
            </div>
          </div>
        </div>
      )}
    </>
  )
}
