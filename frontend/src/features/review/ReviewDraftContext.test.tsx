import { describe, it, expect } from 'vitest'
import { renderHook, act } from '@testing-library/react'
import React from 'react'
import { QueryClientProvider, QueryClient } from '@tanstack/react-query'
import { ReviewDraftProvider, useReviewDraft } from './ReviewDraftContext'
import type { Package } from '../../types'

const mockPackage: Package = {
  id: 'pkg_1',
  hash: 'hash_123',
  approved: false,
  created: '2026-09-05T12:00:00Z',
  job_id: 'job_1',
  profile_revision: 1,
  profile: {
    name: 'Test User',
    headline: 'Developer',
    email: 'test@example.com',
    phone: '123',
    location: 'Remote',
    links: [],
    sections: [],
    source_file: 'cv.pdf',
    revision: 1,
  },
  score: 80,
  requirements: [
    {
      text: 'React experience',
      priority: 'required',
      source_quote: 'Must know React',
      support: 'full',
      weight: 3,
      evidence_ids: ['e1'],
      evidence: [{ id: 'e1', text: 'Built React apps' }],
      explanation: 'Matches profile',
    },
  ],
  changes: [],
  mode: 'local',
  note: 'Test note',
  cv_reviewed: false,
  coverage_reviewed: false,
  answers: { q1: 'initial answer' },
  form: null,
  files: {},
}

describe('ReviewDraftContext', () => {
  it('initializes from package data and detects changes as dirty', () => {
    const qc = new QueryClient()
    const wrapper = ({ children }: { children: React.ReactNode }) => (
      <QueryClientProvider client={qc}>
        <ReviewDraftProvider jobId="job_1" pkg={mockPackage}>
          {children}
        </ReviewDraftProvider>
      </QueryClientProvider>
    )

    const { result } = renderHook(() => useReviewDraft(), { wrapper })

    expect(result.current.cvChecked).toBe(false)
    expect(result.current.isDirty).toBe(false)

    act(() => {
      result.current.setCVChecked(true)
    })

    expect(result.current.cvChecked).toBe(true)
    expect(result.current.isDirty).toBe(true)

    act(() => {
      result.current.resetToPackage()
    })

    expect(result.current.cvChecked).toBe(false)
    expect(result.current.isDirty).toBe(false)
  })
})
