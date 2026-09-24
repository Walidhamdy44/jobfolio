export interface FieldError {
  loc: (string | number)[]
  msg: string
  type: string
}

export class ApiError extends Error {
  status: number
  fieldErrors?: Record<string, string>

  constructor(message: string, status = 500, fieldErrors?: Record<string, string>) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.fieldErrors = fieldErrors
  }
}

export function parseFastApiError(data: unknown, status: number): ApiError {
  if (typeof data === 'object' && data !== null) {
    const record = data as Record<string, unknown>
    if (typeof record.detail === 'string') {
      return new ApiError(record.detail, status)
    }
    if (Array.isArray(record.detail)) {
      const fieldErrors: Record<string, string> = {}
      const msgs: string[] = []
      for (const err of record.detail) {
        if (typeof err === 'object' && err !== null) {
          const loc = (err as FieldError).loc || []
          const msg = (err as FieldError).msg || 'Invalid field'
          const field = String(loc[loc.length - 1] || 'field')
          fieldErrors[field] = msg
          msgs.push(`${field}: ${msg}`)
        }
      }
      return new ApiError(msgs.join(', ') || 'Validation error', status, fieldErrors)
    }
  }
  return new ApiError('The local service is unavailable.', status)
}
