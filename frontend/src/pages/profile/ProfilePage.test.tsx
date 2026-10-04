import { afterEach, describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { createMemoryRouter, Outlet, RouterProvider } from 'react-router-dom'
import { ProfilePage } from './ProfilePage'
import type { Bootstrap, Profile } from '../../types'

afterEach(() => vi.unstubAllGlobals())

const candidate: Profile = {
  name: 'Upload Candidate',
  headline: 'Frontend Engineer',
  email: 'upload@example.com',
  phone: '',
  location: 'Cairo, Egypt',
  links: [],
  sections: [{ title: 'Summary', items: [{ id: 'e1', text: 'Frontend engineer with confirmed experience.' }] }],
  source_file: 'master_cv_0123456789abcdef0123456789abcdef.pdf',
  revision: 0,
}

function renderProfilePage() {
  const data = {
    profile: null,
    preferences: null,
    jobs: [],
    runs: [],
    events: [],
    search_results: { items: [] },
    connections: {
      provider: 'openrouter', connected: false, model: '', base_url: '', search_provider: 'free',
      free_search_ready: true, brave: false, openai: false, openrouter: false, opencode: false,
    },
  } as unknown as Bootstrap
  const router = createMemoryRouter([
    {
      path: '/profile',
      element: <Outlet context={{ data, setToast: vi.fn() }} />,
      children: [{ index: true, element: <ProfilePage /> }],
    },
  ], { initialEntries: ['/profile'] })
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
    </QueryClientProvider>
  )
}

describe('ProfilePage master CV upload', () => {
  it('lets an empty workspace upload a PDF and review the locally parsed profile draft', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ profile: candidate, ok: true }),
    })
    vi.stubGlobal('fetch', fetchMock)
    const { container } = renderProfilePage()

    expect(screen.getByRole('heading', { name: 'Upload your master CV' })).toBeDefined()
    const input = container.querySelector('input[type="file"]')
    const file = new File(['%PDF-1.4'], 'candidate.pdf', { type: 'application/pdf' })
    fireEvent.change(input!, { target: { files: [file] } })

    expect(await screen.findByDisplayValue('Upload Candidate')).toBeDefined()
    expect(screen.getByText(/Review the extracted profile, then save/)).toBeDefined()
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(1))
    const [url, options] = fetchMock.mock.calls[0]
    expect(url).toBe('/api/profile/master-cv')
    expect(options.headers['Content-Type']).toBe('application/pdf')
  })
})
