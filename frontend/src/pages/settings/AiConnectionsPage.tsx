import React, { useState } from 'react'
import { useOutletContext, useNavigate } from 'react-router-dom'
import { Sparkles, ArrowUpRight, Check, Search } from 'lucide-react'
import { Button } from '../../shared/ui/Button'
import { Field } from '../../shared/ui/Field'
import { Notice } from '../../shared/ui/Notice'
import {
  useSaveSettingsMutation,
  useSearchMutation,
} from '../../features/workspace/queries'
import type { Bootstrap } from '../../types'

export function AiConnectionsPage() {
  const navigate = useNavigate()
  const { data, setToast } = useOutletContext<{
    data?: Bootstrap
    setToast: (msg: string) => void
  }>()

  const connections = data?.connections

  const [provider, setProvider] = useState(connections?.provider || 'openrouter')
  const [apiKey, setApiKey] = useState('')
  const [model, setModel] = useState(connections?.model || 'minimax/minimax-m3:free')
  const [baseUrl, setBaseUrl] = useState(connections?.base_url || '')

  const saveSettingsMutation = useSaveSettingsMutation()
  const searchMutation = useSearchMutation()

  const freeModels = [
    { id: 'minimax/minimax-m3:free', label: 'MiniMax M3 (Free & Recommended)' },
    { id: 'openrouter/free', label: 'Auto Free Router' },
    { id: 'z-ai/glm-5.2:free', label: 'GLM 5.2 (Free)' },
    { id: 'google/gemma-4-31b-it:free', label: 'Gemma 31B (Free)' },
    { id: 'nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free', label: 'Nemotron 30B (Free)' },
  ]

  const tokenRouterModels = [
    { id: 'z-ai/glm-5.3-free', label: 'GLM 5.3 (Free Tier)' },
    { id: 'trustedrouter/free', label: 'TrustedRouter Free' },
    { id: 'z-ai/glm-5.3-flash', label: 'GLM 5.3 Flash' },
  ]

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault()
    try {
      await saveSettingsMutation.mutateAsync({
        provider,
        model,
        base_url: baseUrl || undefined,
        search_provider: connections?.search_provider || 'free',
        ...(apiKey ? { api_key: apiKey } : {}),
      })
      setApiKey('')
      setToast('AI connections saved.')
    } catch (err) {
      setToast((err as Error).message)
    }
  }

  const handleSaveAndSearch = async () => {
    try {
      await saveSettingsMutation.mutateAsync({
        provider,
        model,
        base_url: baseUrl || undefined,
        search_provider: connections?.search_provider || 'free',
        ...(apiKey ? { api_key: apiKey } : {}),
      })
      setApiKey('')
      await searchMutation.mutateAsync()
      setToast('Connections saved. Searching opportunities with updated tools…')
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
            <Sparkles size={23} />
            <h2>AI CV Tailoring & Audit</h2>
          </div>
          <span className={`tag ${connections?.connected ? 'connected' : ''}`}>
            {connections?.connected ? `Key saved (${connections.provider}; not verified)` : 'Key needed'}
          </span>
        </div>
        <p>
          Extract job criteria, tailor relevant CV statements, and audit requirement coverage before
          you review.
        </p>

        {/* Semantic Provider Choices */}
        <fieldset style={{ border: 0, padding: 0, margin: '0 0 20px 0' }}>
          <legend style={{ fontSize: '12px', fontWeight: 650, color: '#3f5546', marginBottom: '10px' }}>
            AI Provider
          </legend>
          <div className="provider-toggle">
            <div
              className={`provider-card ${provider === 'openrouter' ? 'selected' : ''}`}
              onClick={() => {
                setProvider('openrouter')
                if (!model.includes(':free') && !model.includes('openrouter')) {
                  setModel('minimax/minimax-m3:free')
                }
              }}
              role="button"
              tabIndex={0}
              onKeyDown={(e) => {
                if (e.key === 'Enter' || e.key === ' ') setProvider('openrouter')
              }}
            >
              <strong>
                OpenRouter <span className="free-badge">Free Models</span>
              </strong>
              <small>MiniMax M3, GLM 5.2, Gemma 31B. Works with a free $0 balance key.</small>
            </div>

            <div
              className={`provider-card ${provider === 'tokenrouter' ? 'selected' : ''}`}
              onClick={() => {
                setProvider('tokenrouter')
                setModel('z-ai/glm-5.3-free')
              }}
              role="button"
              tabIndex={0}
              onKeyDown={(e) => {
                if (e.key === 'Enter' || e.key === ' ') setProvider('tokenrouter')
              }}
            >
              <strong>
                TokenRouter <span className="free-badge">GLM 5.3 Free</span>
              </strong>
              <small>Free tier router for GLM-5.3 and open models (tr_... keys).</small>
            </div>

            <div
              className={`provider-card ${provider === 'opencode' ? 'selected' : ''}`}
              onClick={() => {
                setProvider('opencode')
                setModel('opencode/free')
              }}
              role="button"
              tabIndex={0}
              onKeyDown={(e) => {
                if (e.key === 'Enter' || e.key === ' ') setProvider('opencode')
              }}
            >
              <strong>OpenCode</strong>
              <small>Zen free tier models. Simple and open.</small>
            </div>

            <div
              className={`provider-card ${provider === 'openai' ? 'selected' : ''}`}
              onClick={() => {
                setProvider('openai')
                setModel('gpt-4.1-mini')
              }}
              role="button"
              tabIndex={0}
              onKeyDown={(e) => {
                if (e.key === 'Enter' || e.key === ' ') setProvider('openai')
              }}
            >
              <strong>OpenAI</strong>
              <small>Official API (GPT-4.1 mini, GPT-4o).</small>
            </div>

            <div
              className={`provider-card ${provider === 'custom' ? 'selected' : ''}`}
              onClick={() => {
                setProvider('custom')
                if (!baseUrl) setBaseUrl('http://localhost:11434/v1')
              }}
              role="button"
              tabIndex={0}
              onKeyDown={(e) => {
                if (e.key === 'Enter' || e.key === ' ') setProvider('custom')
              }}
            >
              <strong>Local / Custom</strong>
              <small>Ollama, LMStudio, vLLM or custom OpenAI-compatible endpoint.</small>
            </div>
          </div>
        </fieldset>

        {/* Free Models Selector */}
        {provider === 'openrouter' && (
          <div className="field">
            <span>Recommended Free Models</span>
            <div className="model-pills" role="radiogroup" aria-label="OpenRouter models">
              {freeModels.map((m) => (
                <button
                  type="button"
                  key={m.id}
                  role="radio"
                  aria-checked={model === m.id}
                  className={`model-pill ${model === m.id ? 'active' : ''}`}
                  onClick={() => setModel(m.id)}
                >
                  {m.label}
                </button>
              ))}
            </div>
          </div>
        )}

        {provider === 'tokenrouter' && (
          <div className="field">
            <span>Available Models</span>
            <div className="model-pills" role="radiogroup" aria-label="TokenRouter models">
              {tokenRouterModels.map((m) => (
                <button
                  type="button"
                  key={m.id}
                  role="radio"
                  aria-checked={model === m.id}
                  className={`model-pill ${model === m.id ? 'active' : ''}`}
                  onClick={() => setModel(m.id)}
                >
                  {m.label}
                </button>
              ))}
            </div>
          </div>
        )}

        <Field label="Model identifier" hint="Enter any model name supported by your selected provider." required>
          <input
            value={model}
            required
            onChange={(e) => setModel(e.target.value)}
            placeholder="e.g. minimax/minimax-m3:free"
          />
        </Field>

        {provider === 'custom' && (
          <Field
            label="Base URL"
            hint="OpenAI-compatible base endpoint (e.g. http://localhost:11434/v1 for Ollama)"
          >
            <input
              value={baseUrl}
              onChange={(e) => setBaseUrl(e.target.value)}
              placeholder="http://localhost:11434/v1"
            />
          </Field>
        )}

        <Field
          label={
            provider === 'custom'
              ? 'API key (optional for local)'
              : `${
                  provider === 'openrouter'
                    ? 'OpenRouter'
                    : provider === 'tokenrouter'
                    ? 'TokenRouter'
                    : provider === 'opencode'
                    ? 'OpenCode'
                    : 'OpenAI'
                } API key`
          }
          hint="Leave blank to keep the saved key."
        >
          <input
            type="password"
            autoComplete="new-password"
            value={apiKey}
            onChange={(e) => setApiKey(e.target.value)}
            placeholder={provider === 'custom' ? 'Optional key' : 'Enter API key'}
          />
        </Field>

        {provider === 'openrouter' && (
          <a
            className="text-button"
            href="https://openrouter.ai/keys"
            target="_blank"
            rel="noreferrer"
          >
            Get a free OpenRouter key ($0 balance required)
            <ArrowUpRight size={14} />
          </a>
        )}
        {provider === 'tokenrouter' && (
          <a
            className="text-button"
            href="https://tokenrouter.io"
            target="_blank"
            rel="noreferrer"
          >
            Manage TokenRouter API keys (tokenrouter.io)
            <ArrowUpRight size={14} />
          </a>
        )}
        {provider === 'openai' && (
          <a
            className="text-button"
            href="https://platform.openai.com/api-keys"
            target="_blank"
            rel="noreferrer"
          >
            Manage OpenAI API keys
            <ArrowUpRight size={14} />
          </a>
        )}

        <p className="small">
          CV text and requirements are sent only when you click &ldquo;Tailor with AI&rdquo;. Contact
          information (phone, email, full address) is excluded from AI prompts.
        </p>
      </section>

      <Notice>
        Keys saved here go to your operating system’s credential store. Your CV, job history, and
        documents are stored in this app’s local data folder.
      </Notice>

      <div className="form-actions">
        <span className="muted">Saved keys are never shown in the dashboard.</span>
        <div className="button-group">
          <Button type="submit" disabled={isBusy} loading={saveSettingsMutation.isPending}>
            Save connections
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
