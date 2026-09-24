import { ApiError, parseFastApiError } from './errors'

export interface RequestOptions {
  method?: string
  body?: unknown
  signal?: AbortSignal
  headers?: Record<string, string>
}

export async function apiClient<T = unknown>(
  path: string,
  options: RequestOptions = {}
): Promise<T> {
  const { method = 'GET', body, signal, headers = {} } = options

  const isMutation = !['GET', 'HEAD', 'OPTIONS'].includes(method.toUpperCase())
  const requestHeaders: Record<string, string> = {
    Accept: 'application/json',
    ...headers,
  }

  if (isMutation) {
    requestHeaders['X-Job-Agent'] = 'local'
  }

  let requestBody: string | undefined
  if (body !== undefined) {
    requestHeaders['Content-Type'] = 'application/json'
    requestBody = JSON.stringify(body)
  }

  let res: Response
  try {
    res = await fetch(`/api${path}`, {
      method,
      headers: requestHeaders,
      body: requestBody,
      signal,
    })
  } catch (err: unknown) {
    if ((err as Error)?.name === 'AbortError') {
      throw err
    }
    throw new ApiError(
      'Cannot connect to local backend. Ensure the server is running on port 8765.',
      0
    )
  }

  if (res.status === 204) {
    return {} as T
  }

  if (!res.ok) {
    let errorData: unknown
    try {
      errorData = await res.json()
    } catch {
      errorData = { detail: await res.text().catch(() => res.statusText) }
    }
    throw parseFastApiError(errorData, res.status)
  }

  return res.json() as Promise<T>
}
