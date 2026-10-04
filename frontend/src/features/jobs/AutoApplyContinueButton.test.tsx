import { describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen } from '@testing-library/react'
import type { Job, Run } from '../../types'
import { AutoApplyContinueButton } from './AutoApplyContinueButton'

const job: Job = {
  id: 'job-1',
  title: 'Frontend Engineer',
  company: 'Example employer',
  location: 'Cairo',
  url: 'https://example.com/job',
  description: 'Build frontend applications.',
  platform: 'linkedin',
  state: 'needs_input',
  input_request: 'Complete the salary field.',
  created: '2026-09-28T10:00:00Z',
  verified: true,
}

const run: Run = {
  id: 'run-1',
  kind: 'auto_apply',
  target: 'job-1',
  state: 'running',
  message: 'Input needed: Complete the salary field.',
  created: '2026-09-28T10:00:00Z',
}

describe('AutoApplyContinueButton', () => {
  it('is available only while the matching Auto-Apply run waits for input', () => {
    const { rerender } = render(
      <AutoApplyContinueButton job={job} run={run} isPending={false} onContinue={vi.fn()} />,
    )
    expect(screen.getByRole('button', { name: "I've finished — continue" })).toBeDefined()

    rerender(
      <AutoApplyContinueButton job={job} run={{ ...run, state: 'completed' }} isPending={false} onContinue={vi.fn()} />,
    )
    expect(screen.queryByRole('button', { name: "I've finished — continue" })).toBeNull()
  })

  it('signals that the user finished the pending fields', () => {
    const onContinue = vi.fn()
    render(<AutoApplyContinueButton job={job} run={run} isPending={false} onContinue={onContinue} />)

    fireEvent.click(screen.getByRole('button', { name: "I've finished — continue" }))

    expect(onContinue).toHaveBeenCalledTimes(1)
  })
})
