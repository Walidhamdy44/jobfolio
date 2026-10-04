import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { MemoryRouter, Outlet, Route, Routes, useParams } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { JobCoverageImprovePage } from './JobCoverageImprovePage'
import type { CVImprovementDraft, Job, Package } from '../../types'

const mutations = vi.hoisted(() => ({
  draft: { mutateAsync: vi.fn(), isPending: false },
  apply: { mutateAsync: vi.fn(), isPending: false },
}))

vi.mock('../../features/jobs/queries', () => ({
  useDraftCoverageImprovementsMutation: () => mutations.draft,
  useApplyCoverageImprovementsMutation: () => mutations.apply,
}))

vi.mock('../../features/review/ReviewDraftContext', () => ({
  useReviewDraft: () => ({ isDirty: false, isConflicted: false, resetToPackage: vi.fn() }),
}))

const job: Job = {
  id: 'job-1', title: 'Frontend Engineer', company: 'Example', location: 'Remote', url: '',
  description: 'Build web applications.', platform: 'manual', state: 'awaiting_review',
  created: '', verified: true,
}

const pkg: Package = {
  id: 'package-1', hash: 'hash-1', approved: false, created: '', job_id: 'job-1', profile_revision: 1,
  profile: {
    name: 'Test User', headline: 'Frontend Engineer', email: '', phone: '', location: 'Remote', links: [],
    source_file: '', revision: 1,
    sections: [{ title: 'Summary', items: [{ id: 'source-1', text: 'Built accessible React interfaces.' }] }],
  },
  score: 40,
  requirements: [
    {
      text: 'Production Kubernetes experience', priority: 'required', source_quote: 'Production Kubernetes experience',
      support: 'missing', weight: 3, evidence_ids: [], evidence: [], explanation: 'No support found.',
    },
    {
      text: 'React and accessibility experience', priority: 'preferred', source_quote: 'React and accessibility experience',
      support: 'missing', weight: 1, evidence_ids: ['source-1'],
      evidence: [{ id: 'source-1', text: 'Built accessible React interfaces.' }], explanation: 'Wording can be clearer.',
    },
  ],
  changes: [], mode: 'ai', note: 'AI-assessed', cv_reviewed: false, coverage_reviewed: false,
  answers: {}, form: null, files: {},
}

function JobScope() {
  const { jobId = '' } = useParams()
  return (
    <Outlet context={{
      job: { ...job, id: jobId }, pkg, isLocked: false, bootstrap: { connections: { connected: true } },
      setToast: vi.fn(),
    }} />
  )
}

function renderPage() {
  return render(
    <MemoryRouter initialEntries={['/jobs/job-1/coverage/improve']}>
      <Routes>
        <Route path="/jobs/:jobId" element={<JobScope />}>
          <Route path="coverage/improve" element={<JobCoverageImprovePage />} />
          <Route path="cv" element={<h2>CV review destination</h2>} />
          <Route path="coverage" element={<h2>Coverage review destination</h2>} />
        </Route>
      </Routes>
    </MemoryRouter>
  )
}

describe('JobCoverageImprovePage', () => {
  beforeEach(() => {
    mutations.draft.mutateAsync.mockReset()
    mutations.apply.mutateAsync.mockReset()
    mutations.draft.isPending = false
    mutations.apply.isPending = false
  })

  it('requires user evidence for unsupported gaps and applies only a selected audited edit', async () => {
    const suggestion = {
      id: 'suggestion-1', action: 'rewrite' as const, requirement_indices: [1], evidence_id: 'source-1',
      section: 'Summary', before: 'Built accessible React interfaces.',
      after: 'Built accessible React interfaces with React.',
      source_evidence: 'Built accessible React interfaces.', evidence_confirmed: false,
    }
    const draft: CVImprovementDraft = {
      draft_id: 'draft-1', package_id: pkg.id, profile_revision: 1,
      selections: [{ requirement_index: 1, evidence_text: '', evidence_confirmed: false }],
      suggestions: [suggestion], unresolved: [],
    }
    mutations.draft.mutateAsync.mockResolvedValue(draft)
    mutations.apply.mutateAsync.mockResolvedValue({ ok: true, package_id: 'package-2', score: 50, change_count: 1 })

    renderPage()
    expect(screen.getByRole('heading', { name: 'Final CV preview' })).toBeDefined()
    expect(within(screen.getByLabelText('CV preview document')).getByText('Built accessible React interfaces.')).toBeDefined()

    const draftButton = screen.getByRole('button', { name: /Draft selected edits/ })
    fireEvent.click(screen.getByRole('checkbox', { name: 'Select Production Kubernetes experience' }))
    expect((draftButton as HTMLButtonElement).disabled).toBe(true)
    fireEvent.change(screen.getByLabelText('What experience or qualification supports this?'), {
      target: { value: 'Used Kubernetes to deploy and monitor production services.' },
    })
    fireEvent.click(screen.getByRole('checkbox', { name: /I confirm this is accurate experience/ }))
    expect((draftButton as HTMLButtonElement).disabled).toBe(false)

    fireEvent.click(screen.getByRole('checkbox', { name: 'Select React and accessibility experience' }))
    fireEvent.click(draftButton)
    await screen.findByRole('heading', { name: /AI-audited suggestions/ })
    expect(mutations.draft.mutateAsync).toHaveBeenCalledWith({
      package_hash: pkg.hash,
      selections: [
        { requirement_index: 0, evidence_text: 'Used Kubernetes to deploy and monitor production services.', evidence_confirmed: true },
        { requirement_index: 1, evidence_text: '', evidence_confirmed: false },
      ],
    })

    fireEvent.click(screen.getByRole('checkbox', { name: 'Include edit' }))
    expect(within(screen.getByLabelText('CV preview document')).getByText('Built accessible React interfaces with React.')).toBeDefined()
    fireEvent.click(screen.getByRole('button', { name: /Apply selected edits/ }))
    await waitFor(() => expect(mutations.apply.mutateAsync).toHaveBeenCalledWith({
      package_hash: pkg.hash, draft_id: 'draft-1', suggestion_ids: ['suggestion-1'],
    }))
    expect(await screen.findByText('CV review destination')).toBeDefined()
  })
})
