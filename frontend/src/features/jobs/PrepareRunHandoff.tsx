import { useEffect, useRef } from 'react'
import { Button } from '../../shared/ui/Button'

export type ResumablePrepareRun = { id: string; message: string; created: string }

export function ResumePreparationButton({
  run,
  disabled,
  onResume,
}: {
  run?: ResumablePrepareRun | null
  disabled: boolean
  onResume: (runId: string) => void
}) {
  if (!run) return null
  return (
    <Button kind="primary" disabled={disabled} loading={disabled} onClick={() => onResume(run.id)}>
      Resume preparation
    </Button>
  )
}

export function PrepareRunHandoff({
  jobId,
  pendingRunId,
  runState,
  onClear,
  navigate,
  locationPath,
  refreshJob,
}: {
  jobId: string
  pendingRunId: string | null
  runState?: string
  onClear: () => void
  navigate: (path: string) => void
  locationPath: string
  refreshJob: () => Promise<unknown>
}) {
  const pathname = useRef(locationPath)
  const navigateRef = useRef(navigate)
  const refreshRef = useRef(refreshJob)
  const handledRunId = useRef<string | null>(null)
  pathname.current = locationPath
  navigateRef.current = navigate
  refreshRef.current = refreshJob

  useEffect(() => {
    if (!pendingRunId) {
      handledRunId.current = null
      return
    }
    if (!['completed', 'failed', 'interrupted'].includes(runState || '') || handledRunId.current === pendingRunId) return
    handledRunId.current = pendingRunId
    if (runState === 'failed' || runState === 'interrupted') {
      onClear()
      return
    }
    if (runState !== 'completed') return

    const jobPrefix = `/jobs/${jobId}/`
    if (!pathname.current.startsWith(jobPrefix)) {
      onClear()
      return
    }

    let cancelled = false
    void refreshRef.current().finally(() => {
      if (cancelled) return
      if (pathname.current.startsWith(jobPrefix)) {
        navigateRef.current(`${jobPrefix}cv`)
      }
      onClear()
    })
    return () => {
      cancelled = true
    }
  }, [jobId, onClear, pendingRunId, runState])

  return null
}
