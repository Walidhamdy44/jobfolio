import { useState } from 'react'
import { describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { PrepareRunHandoff, ResumePreparationButton } from './PrepareRunHandoff'

function HandoffHarness({
  runState,
  onClear,
  refreshJob,
}: {
  runState?: string
  onClear: () => void
  refreshJob: () => Promise<unknown>
}) {
  const [path, setPath] = useState('/jobs/job-1/application')
  return (
    <>
      <PrepareRunHandoff
        jobId="job-1"
        pendingRunId="run-1"
        runState={runState}
        onClear={onClear}
        navigate={setPath}
        locationPath={path}
        refreshJob={refreshJob}
      />
      <button onClick={() => setPath('/opportunities')}>Leave job</button>
      <p>{path}</p>
    </>
  )
}

describe('AI preparation review handoff', () => {
  it('opens the CV tab after the tracked run completes on the same job', async () => {
    const onClear = vi.fn()
    const refreshJob = vi.fn().mockResolvedValue(undefined)
    render(<HandoffHarness runState="completed" onClear={onClear} refreshJob={refreshJob} />)

    expect(await screen.findByText('/jobs/job-1/cv')).toBeDefined()
    await waitFor(() => expect(onClear).toHaveBeenCalledTimes(1))
    expect(refreshJob).toHaveBeenCalledTimes(1)
  })

  it('does not pull the user back when the run completes elsewhere', async () => {
    const onClear = vi.fn()
    const refreshJob = vi.fn().mockResolvedValue(undefined)
    const { rerender } = render(<HandoffHarness onClear={onClear} refreshJob={refreshJob} />)
    fireEvent.click(screen.getByRole('button', { name: 'Leave job' }))

    rerender(<HandoffHarness runState="completed" onClear={onClear} refreshJob={refreshJob} />)

    expect(screen.getByText('/opportunities')).toBeDefined()
    await waitFor(() => expect(onClear).toHaveBeenCalledTimes(1))
    expect(refreshJob).not.toHaveBeenCalled()
  })

  it('shows and invokes the Resume preparation action only for an eligible run', () => {
    const onResume = vi.fn()
    const run = { id: 'resume-1', message: 'Interrupted', created: '2026-09-28T12:00:00Z' }
    const { rerender } = render(<ResumePreparationButton run={null} disabled={false} onResume={onResume} />)
    expect(screen.queryByRole('button', { name: 'Resume preparation' })).toBeNull()

    rerender(<ResumePreparationButton run={run} disabled={false} onResume={onResume} />)
    fireEvent.click(screen.getByRole('button', { name: 'Resume preparation' }))
    expect(onResume).toHaveBeenCalledWith('resume-1')
  })
})
