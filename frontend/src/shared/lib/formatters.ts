export function formatDate(dateString: string): string {
  try {
    return new Date(dateString).toLocaleDateString(undefined, {
      month: 'short',
      day: 'numeric',
    })
  } catch {
    return dateString
  }
}

export function formatScore(score?: number): string {
  if (score === undefined || score === null) return 'N/A'
  return `${Math.round(score)}%`
}

export function truncate(str: string, maxLen = 120): string {
  if (!str) return ''
  return str.length > maxLen ? str.slice(0, maxLen) + '…' : str
}

export const STATE_LABELS: Record<string, string> = {
  shortlisted: 'Saved',
  awaiting_review: 'Needs review',
  approved: 'Approved',
  submitting: 'Submitting',
  submitted: 'Submitted',
  skipped: 'Skipped',
  needs_input: 'Needs your input',
  uncertain: 'Check submission',
}
