import { useEffect, useRef } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '../../shared/api/client'
import type { Bootstrap, Preferences, Profile } from '../../types'
import { jobKeys } from '../jobs/queries'

export const workspaceKeys = {
  all: ['workspace'] as const,
  bootstrap: ['workspace', 'bootstrap'] as const,
}

export function useBootstrapQuery() {
  const qc = useQueryClient()
  const prevActiveRef = useRef<boolean>(false)

  const query = useQuery<Bootstrap>({
    queryKey: workspaceKeys.bootstrap,
    queryFn: ({ signal }) => apiClient<Bootstrap>('/workspace', { signal }),
    refetchInterval: (q) => {
      const data = q.state.data
      if (!data) return false
      const hasActiveRun = data.runs?.some((r) => ['queued', 'running'].includes(r.state))
      return hasActiveRun ? 1000 : false
    },
  })

  useEffect(() => {
    const data = query.data
    if (!data) return
    const hasActiveRun = data.runs?.some((r) => ['queued', 'running'].includes(r.state))
    if (prevActiveRef.current && !hasActiveRun) {
      // Active run finished! Invalidate all job queries so detail views immediately reflect new packages/status
      void qc.invalidateQueries({ queryKey: jobKeys.all })
    }
    prevActiveRef.current = Boolean(hasActiveRun)
  }, [query.data, qc])

  return query
}

export function useSavePreferencesMutation() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (preferences: Preferences) =>
      apiClient<{ ok: boolean }>('/preferences', { method: 'PUT', body: preferences }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: workspaceKeys.bootstrap })
    },
  })
}

export function useSaveSettingsMutation() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (settings: unknown) =>
      apiClient<{ ok: boolean }>('/settings', { method: 'PUT', body: settings }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: workspaceKeys.bootstrap })
    },
  })
}

export function useSaveProfileMutation() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (profile: Profile) =>
      apiClient<{ ok: boolean }>('/profile', { method: 'PUT', body: profile }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: workspaceKeys.bootstrap })
      void qc.invalidateQueries({ queryKey: jobKeys.all })
    },
  })
}

export function useStructureProfileMutation() {
  return useMutation({
    mutationFn: (params: { mode: 'ai' | 'local' }) =>
      apiClient<{ profile: Profile; ok: boolean }>('/profile/structure', {
        method: 'POST',
        body: params,
      }),
  })
}

export function useSearchMutation() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body?: { preferences?: Preferences; search_provider?: string }) =>
      apiClient<{ run_id: string }>('/search', { method: 'POST', body }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: workspaceKeys.bootstrap })
    },
  })
}
