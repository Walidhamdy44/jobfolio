import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter, Routes, Route, Outlet } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { DiscoverPage } from './DiscoverPage'
import type { Bootstrap } from '../../types'

const mockBootstrap: Bootstrap = {
  profile: {
    name: 'Test Candidate',
    headline: 'Senior Full Stack Engineer',
    email: 'test@example.com',
    phone: '',
    location: 'Remote',
    links: [],
    sections: [],
    source_file: '',
    revision: 1,
  },
  preferences: {
    titles: ['Software Engineer'],
    location: 'Remote',
    remote_only: true,
    excluded_companies: [],
    excluded_keywords: [],
    salary_note: '',
    work_authorization: '',
    confirmed: true,
  },
  jobs: [],
  runs: [],
  events: [],
  search_results: {
    at: '2026-09-05T12:00:00Z',
    items: [
      {
        url: 'https://example.com/job1',
        title: 'Senior Frontend Developer',
        snippet: 'React and TypeScript opportunity at Jobicy',
        platform: 'jobicy',
        source: 'Jobicy',
      },
      {
        url: 'https://example.com/job2',
        title: 'Backend Go Engineer',
        snippet: 'Distributed systems at Remotive',
        platform: 'remotive',
        source: 'Remotive',
      },
    ],
  },
  connections: {
    provider: 'opencode',
    connected: true,
    model: 'minimax-01',
    base_url: '',
    search_provider: 'free',
    free_search_ready: true,
    brave: false,
    openai: false,
    openrouter: false,
    opencode: true,
  },
}

function renderDiscoverPage(initialUrl = '/discover') {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })

  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={[initialUrl]}>
        <Routes>
          <Route element={<Outlet context={{ data: mockBootstrap, setToast: vi.fn() }} />}>
            <Route path="/discover" element={<DiscoverPage />} />
          </Route>
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>
  )
}

describe('DiscoverPage (QA-06, QA-07, QA-08, QA-10)', () => {
  it('displays feed platform names instead of manual (QA-10)', () => {
    renderDiscoverPage('/discover')
    expect(screen.getByText('Jobicy')).toBeDefined()
    expect(screen.getByText('Remotive')).toBeDefined()
  })

  it('filters results matching trimmed query (QA-07)', () => {
    renderDiscoverPage('/discover?q=%20frontend%20')
    expect(screen.getByText('Senior Frontend Developer')).toBeDefined()
    expect(screen.queryByText('Backend Go Engineer')).toBeNull()
  })

  it('renders unmatched search empty state with clear button (QA-08)', () => {
    renderDiscoverPage('/discover?q=nonexistentqueryxyz')
    expect(screen.getByText('No results match your filter')).toBeDefined()
    expect(screen.getByText('Clear search filter')).toBeDefined()
  })

  it('handles invalid out-of-bounds page param gracefully (QA-06)', () => {
    // There are 2 items, ITEMS_PER_PAGE=25 => totalPages=1. page=999 should clamp and still display items
    renderDiscoverPage('/discover?page=999')
    expect(screen.getByText('Senior Frontend Developer')).toBeDefined()
    expect(screen.getByText('Backend Go Engineer')).toBeDefined()
  })

  it('handles non-numeric page param gracefully (QA-06)', () => {
    renderDiscoverPage('/discover?page=invalid')
    expect(screen.getByText('Senior Frontend Developer')).toBeDefined()
  })
})
