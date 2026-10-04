import { Check } from 'lucide-react'
import { Button } from '../../shared/ui/Button'
import type { Job, Run } from '../../types'

type Props = {
  job?: Job
  run?: Run
  isPending: boolean
  onContinue: () => void
}

export function AutoApplyContinueButton({ job, run, isPending, onContinue }: Props) {
  const isWaitingForUser = Boolean(
    job &&
    run &&
    run.target === job.id &&
    run.kind === 'auto_apply' &&
    run.state === 'running' &&
    run.message.startsWith('Input needed:') &&
    job.state === 'needs_input' &&
    job.input_request,
  )

  if (!isWaitingForUser) return null

  return (
    <Button
      kind="primary"
      disabled={isPending}
      loading={isPending}
      onClick={onContinue}
      title="Recheck the form and continue filling it. This will not submit the application."
    >
      <Check size={14} />
      {isPending ? 'Continuing…' : "I've finished — continue"}
    </Button>
  )
}
