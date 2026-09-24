import React, { useState } from 'react'
import { useOutletContext, useNavigate } from 'react-router-dom'
import { Search, ArrowUpRight, Check } from 'lucide-react'
import { Button } from '../../shared/ui/Button'
import { Field } from '../../shared/ui/Field'
import { Notice } from '../../shared/ui/Notice'
import {
  useSaveSettingsMutation,
  useSearchMutation,
} from '../../features/workspace/queries'
import type { Bootstrap } from '../../types'

export function SearchSourcesPage() {
  const navigate = useNavigate()
  const { data, setToast } = useOutletContext<{
    data?: Bootstrap
    setToast: (msg: string) => void
  }>()

  const connections = data?.connections

  const [searchProvider, setSearchProvider] = useState<'free' | 'brave' | 'serper'>(
    (connections?.search_provider as 'free' | 'brave' | 'serper') || 'free'
  )
  const [braveKey, setBraveKey] = useState('')
  const [serperKey, setSerperKey] = useState('')

  const saveSettingsMutation = useSaveSettingsMutation()
  const searchMutation = useSearchMutation()

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault()
    try {
      await saveSettingsMutation.mutateAsync({
        provider: connections?.provider || 'openrouter',
        model: connections?.model || 'minimax/minimax-m3:free',
        search_provider: searchProvider,
        ...(braveKey ? { brave_key: braveKey } : {}),
        ...(serperKey ? { serper_key: serperKey } : {}),
      })
      setBraveKey('')
      setSerperKey('')
      setToast('Search provider settings saved.')
    } catch (err) {
      setToast((err as Error).message)
    }
  }

  const handleSaveAndSearch = async () => {
    try {
      await saveSettingsMutation.mutateAsync({
        provider: connections?.provider || 'openrouter',
        model: connections?.model || 'minimax/minimax-m3:free',
        search_provider: searchProvider,
        ...(braveKey ? { brave_key: braveKey } : {}),
        ...(serperKey ? { serper_key: serperKey } : {}),
      })
      setBraveKey('')
      setSerperKey('')
      await searchMutation.mutateAsync()
      setToast('Search sources saved. Querying opportunities…')
      navigate('/discover')
    } catch (err) {
      setToast((err as Error).message)
    }
  }

  const isBusy = saveSettingsMutation.isPending || searchMutation.isPending

  return (
    <form className="settings-form" onSubmit={handleSave}>
      <section className="editor-panel connection-panel">
        <div className="section-title">
          <div className="connection-title">
            <Search size={23} />
            <h2>Job Search Provider</h2>
          </div>
          <span className="tag connected">
            {searchProvider === 'free'
              ? 'LinkedIn & Feeds Active'
              : searchProvider === 'serper'
              ? connections?.serper
                ? 'Google Jobs Connected'
                : 'Serper Key Required'
              : connections?.brave
              ? 'Brave Connected'
              : 'Brave Not Configured'}
          </span>
        </div>
        <p>Choose how the agent finds new opportunities based on your saved titles and location.</p>

        <fieldset style={{ border: 0, padding: 0, margin: '0 0 20px 0' }}>
          <legend style={{ fontSize: '12px', fontWeight: 650, color: '#3f5546', marginBottom: '10px' }}>
            Discovery Source
          </legend>
          <div className="provider-toggle">
            <div
              className={`provider-card ${searchProvider === 'free' ? 'selected' : ''}`}
              onClick={() => setSearchProvider('free')}
              role="button"
              tabIndex={0}
              onKeyDown={(e) => {
                if (e.key === 'Enter' || e.key === ' ') setSearchProvider('free')
              }}
            >
              <strong>
                LinkedIn & Free Feeds <span className="free-badge">100% Free</span>
              </strong>
              <small>
                Direct LinkedIn Jobs (Egypt, worldwide, and remote), plus WeWorkRemotely, Remotive, Jobicy, and Arbeitnow. Zero API keys required.
              </small>
            </div>

            <div
              className={`provider-card ${searchProvider === 'serper' ? 'selected' : ''}`}
              onClick={() => setSearchProvider('serper')}
              role="button"
              tabIndex={0}
              onKeyDown={(e) => {
                if (e.key === 'Enter' || e.key === ' ') setSearchProvider('serper')
              }}
            >
              <strong>Google Jobs (Serper API)</strong>
              <small>
                Aggregates Google Jobs across LinkedIn, Indeed, Glassdoor, ZipRecruiter, and employer career sites. 2,500 free searches.
              </small>
            </div>

            <div
              className={`provider-card ${searchProvider === 'brave' ? 'selected' : ''}`}
              onClick={() => setSearchProvider('brave')}
              role="button"
              tabIndex={0}
              onKeyDown={(e) => {
                if (e.key === 'Enter' || e.key === ' ') setSearchProvider('brave')
              }}
            >
              <strong>Brave Search API</strong>
              <small>Broad web search across global employer career pages. Requires a Brave Search token.</small>
            </div>
          </div>
        </fieldset>

        {searchProvider === 'serper' && (
          <>
            <Field
              label="Serper Google Jobs API key"
              hint="Sends search terms and location to Google Jobs. Free accounts include 2,500 queries."
            >
              <input
                type="password"
                autoComplete="new-password"
                value={serperKey}
                onChange={(e) => setSerperKey(e.target.value)}
                placeholder={connections?.serper ? '•••••••••••••••• (Connected)' : 'Enter your Serper API key'}
              />
            </Field>
            <a
              className="text-button"
              href="https://serper.dev"
              target="_blank"
              rel="noreferrer"
            >
              Get a free Serper API key (2,500 free searches)
              <ArrowUpRight size={14} />
            </a>
          </>
        )}

        {searchProvider === 'brave' && (
          <>
            <Field
              label="Brave Search API key"
              hint="Search sends only job titles and location filters, never your CV or personal info."
            >
              <input
                type="password"
                autoComplete="new-password"
                value={braveKey}
                onChange={(e) => setBraveKey(e.target.value)}
                placeholder={connections?.brave ? '•••••••••••••••• (Connected)' : 'Enter your Brave search token'}
              />
            </Field>
            <a
              className="text-button"
              href="https://api-dashboard.search.brave.com/"
              target="_blank"
              rel="noreferrer"
            >
              Get a Brave Search API key
              <ArrowUpRight size={14} />
            </a>
          </>
        )}
      </section>

      <Notice>
        Free public tech feeds query remote engineering roles directly from source publishers without rate-limit fees.
      </Notice>

      <div className="form-actions">
        <span className="muted">Preferences determine search role keywords.</span>
        <div className="button-group">
          <Button type="submit" disabled={isBusy} loading={saveSettingsMutation.isPending}>
            Save search sources
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
  )
}
