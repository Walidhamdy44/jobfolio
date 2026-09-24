import React, { useState, useEffect } from 'react'
import { useOutletContext, useNavigate } from 'react-router-dom'
import { Check, Search } from 'lucide-react'
import { Button } from '../../shared/ui/Button'
import { Field } from '../../shared/ui/Field'
import {
  useSavePreferencesMutation,
  useSearchMutation,
} from '../../features/workspace/queries'
import type { Bootstrap, Preferences } from '../../types'

export function PreferencesPage() {
  const navigate = useNavigate()
  const { data, setToast } = useOutletContext<{
    data?: Bootstrap
    setToast: (msg: string) => void
  }>()

  const initialPreferences = data?.preferences

  const [p, setP] = useState<Preferences | null>(initialPreferences || null)

  const savePreferencesMutation = useSavePreferencesMutation()
  const searchMutation = useSearchMutation()

  useEffect(() => {
    if (initialPreferences && !p) {
      setP(initialPreferences)
    }
  }, [initialPreferences])

  if (!p) {
    return <p className="muted">Loading preferences…</p>
  }

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!p) return
    try {
      await savePreferencesMutation.mutateAsync({ ...p, confirmed: true })
      setToast('Search preferences saved.')
    } catch (err) {
      setToast((err as Error).message)
    }
  }

  const handleSaveAndSearch = async () => {
    if (!p) return
    try {
      await searchMutation.mutateAsync({
        preferences: { ...p, confirmed: true },
      })
      setToast('Preferences saved. Searching opportunities with your updated criteria…')
      navigate('/discover')
    } catch (err) {
      setToast((err as Error).message)
    }
  }

  const isBusy = savePreferencesMutation.isPending || searchMutation.isPending

  return (
    <>
      <div className="page-heading">
        <div>
          <h1>Define your next move.</h1>
          <p>Tell the agent what a good opportunity looks like for you.</p>
        </div>
      </div>

      <form className="settings-form" onSubmit={handleSave}>
        <section className="editor-panel">
          <h2>The roles you’re looking for</h2>
          <Field
            label="Target job titles"
            hint="One title per line. Search queries the first four titles across feeds."
            required
          >
            <textarea
              rows={4}
              required
              value={p.titles.join('\n')}
              onChange={(e) => setP({ ...p, titles: e.target.value.split('\n') })}
            />
          </Field>

          <div className="form-grid">
            <Field
              label="Country"
              hint="Target country for LinkedIn, Google Jobs, and job board queries."
            >
              <input
                value={p.country || ''}
                onChange={(e) => setP({ ...p, country: e.target.value })}
                placeholder="For example: Egypt, United States, UAE, Germany"
              />
            </Field>

            <Field
              label="City / Region"
              hint="City or specific metro area (e.g. Cairo, Dubai, London, Berlin)."
            >
              <input
                value={p.location || ''}
                onChange={(e) => setP({ ...p, location: e.target.value })}
                placeholder="For example: Cairo, Alexandria, Dubai"
              />
            </Field>
          </div>

          <div className="form-grid">
            <Field
              label="Date of posting"
              hint="Filter fresh listings on LinkedIn and Google Jobs."
            >
              <select
                value={p.date_posted || 'any'}
                onChange={(e) =>
                  setP({
                    ...p,
                    date_posted: e.target.value as 'any' | 'past_24h' | 'past_week' | 'past_month',
                  })
                }
              >
                <option value="any">Any time (All active listings)</option>
                <option value="past_24h">Past 24 hours (Fresh postings)</option>
                <option value="past_week">Past week (Last 7 days)</option>
                <option value="past_month">Past month (Last 30 days)</option>
              </select>
            </Field>

            <Field
              label="Experience level"
              hint="Seniority target to filter on LinkedIn and boost in candidate ranking."
            >
              <select
                value={p.experience_level || 'any'}
                onChange={(e) =>
                  setP({
                    ...p,
                    experience_level: e.target.value as 'any' | 'entry' | 'mid' | 'senior',
                  })
                }
              >
                <option value="any">All experience levels</option>
                <option value="entry">Entry level / Junior</option>
                <option value="mid">Mid level / Associate</option>
                <option value="senior">Senior / Lead / Principal</option>
              </select>
            </Field>
          </div>

          <div className="form-grid">
            <Field
              label="Workplace type"
              hint="Work arrangement filter for search engines."
            >
              <select
                value={p.workplace_type || (p.remote_only ? 'remote' : 'any')}
                onChange={(e) => {
                  const val = e.target.value as 'any' | 'remote' | 'hybrid' | 'on_site'
                  setP({
                    ...p,
                    workplace_type: val,
                    remote_only: val === 'remote' ? true : p.remote_only,
                  })
                }}
              >
                <option value="any">Any workplace (Remote, Hybrid, On-site)</option>
                <option value="remote">Remote only</option>
                <option value="hybrid">Hybrid</option>
                <option value="on_site">On-site (in-office)</option>
              </select>
            </Field>

            <Field
              label="Job type"
              hint="Employment type filter for search engines."
            >
              <select
                value={p.job_type || 'any'}
                onChange={(e) =>
                  setP({
                    ...p,
                    job_type: e.target.value as 'any' | 'full_time' | 'contract' | 'part_time',
                  })
                }
              >
                <option value="any">All job types</option>
                <option value="full_time">Full-time</option>
                <option value="contract">Contract / Freelance</option>
                <option value="part_time">Part-time</option>
              </select>
            </Field>
          </div>

          <label className="check-field">
            <input
              type="checkbox"
              checked={p.remote_only}
              onChange={(e) =>
                setP({
                  ...p,
                  remote_only: e.target.checked,
                  workplace_type:
                    e.target.checked && p.workplace_type !== 'remote'
                      ? 'remote'
                      : p.workplace_type,
                })
              }
            />
            <span>Prioritize remote roles across all search providers</span>
          </label>
        </section>

        <section className="editor-panel">
          <h2>Preferences and deal-breakers</h2>
          <div className="form-grid">
            <Field label="Excluded companies" hint="One company per line">
              <textarea
                rows={3}
                value={p.excluded_companies.join('\n')}
                onChange={(e) =>
                  setP({
                    ...p,
                    excluded_companies: e.target.value.split('\n').filter(Boolean),
                  })
                }
              />
            </Field>

            <Field label="Excluded keywords" hint="For example: unpaid, internship, principal">
              <textarea
                rows={3}
                value={p.excluded_keywords.join('\n')}
                onChange={(e) =>
                  setP({
                    ...p,
                    excluded_keywords: e.target.value.split('\n').filter(Boolean),
                  })
                }
              />
            </Field>
          </div>

          <Field
            label="Salary preferences"
            hint="Shown during review; not used as an automatic filter."
          >
            <input
              value={p.salary_note}
              onChange={(e) => setP({ ...p, salary_note: e.target.value })}
              placeholder="Currency, minimum, and pay period"
            />
          </Field>

          <Field
            label="Work authorization"
            hint="A reminder for your review. The agent will not infer legal eligibility or answer on your behalf."
          >
            <textarea
              rows={3}
              value={p.work_authorization}
              onChange={(e) => setP({ ...p, work_authorization: e.target.value })}
              placeholder="Where you are authorized to work and any sponsorship requirements"
            />
          </Field>
        </section>

        <div className="form-actions">
          <span className="muted">Your search runs automatically using these parameters.</span>
          <div className="button-group">
            <Button type="submit" disabled={isBusy} loading={savePreferencesMutation.isPending}>
              Save preferences
              <Check size={15} />
            </Button>
            <Button
              type="button"
              kind="primary"
              disabled={isBusy}
              loading={searchMutation.isPending}
              onClick={() => void handleSaveAndSearch()}
            >
              <Search size={15} />
              Save & Find jobs now
            </Button>
          </div>
        </div>
      </form>
    </>
  )
}
