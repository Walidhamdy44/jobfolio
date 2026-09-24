import { describe, it, expect, vi, beforeEach } from 'vitest'
import { apiClient } from './client'
import { ApiError } from './errors'

describe('apiClient', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('adds X-Job-Agent: local header for mutation requests', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ ok: true }),
    })
    globalThis.fetch = fetchMock

    await apiClient('/test', { method: 'POST', body: { name: 'test' } })

    expect(fetchMock).toHaveBeenCalledTimes(1)
    const [url, options] = fetchMock.mock.calls[0]
    expect(url).toBe('/api/test')
    expect(options.method).toBe('POST')
    expect(options.headers['X-Job-Agent']).toBe('local')
    expect(options.headers['Content-Type']).toBe('application/json')
    expect(options.body).toBe(JSON.stringify({ name: 'test' }))
  })

  it('does not send X-Job-Agent header on GET requests', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ data: 'test' }),
    })
    globalThis.fetch = fetchMock

    await apiClient('/bootstrap', { method: 'GET' })

    const [, options] = fetchMock.mock.calls[0]
    expect(options.headers['X-Job-Agent']).toBeUndefined()
  })

  it('throws ApiError on HTTP error status', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: false,
      status: 404,
      json: async () => ({ detail: 'Job not found' }),
    })
    globalThis.fetch = fetchMock

    await expect(apiClient('/jobs/missing')).rejects.toThrow(ApiError)
    await expect(apiClient('/jobs/missing')).rejects.toThrow('Job not found')
  })
})
