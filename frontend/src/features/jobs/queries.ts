import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '../../shared/api/client'
import type { Detail, Job } from '../../types'
import { workspaceKeys } from '../workspace/queries'

export const jobKeys = {
  all: ['jobs'] as const,
  detail: (id: string) => ['jobs', 'detail', id] as const,
}

export function useJobDetailQuery(jobId?: string) {
  const qc = useQueryClient()
  return useQuery<Detail>({
    queryKey: jobKeys.detail(jobId || ''),
    queryFn: ({ signal }) => {
      if (!jobId) throw new Error('Missing job ID')
      return apiClient<Detail>(`/jobs/${jobId}`, { signal })
    },
    enabled: Boolean(jobId),
    staleTime: 0,
    refetchOnMount: 'always',
    refetchInterval: () => {
      // Check if there is an active run targeting this job
      const bootstrap = qc.getQueryData<{ runs?: { target: string | null; state: string }[] }>(
        workspaceKeys.bootstrap
      )
      const isJobRunning = bootstrap?.runs?.some(
        (r) => r.target === jobId && ['queued', 'running'].includes(r.state)
      )
      return isJobRunning ? 1000 : false
    },
  })
}

export function useUpdateJobMutation(jobId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (payload: { title?: string; company?: string; location?: string; description?: string }) =>
      apiClient<{ job: Job; ok: boolean }>(`/jobs/${jobId}`, { method: 'PATCH', body: payload }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: workspaceKeys.bootstrap })
      void qc.invalidateQueries({ queryKey: jobKeys.detail(jobId) })
    },
  })
}

export function useRefetchJobMutation(jobId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: () =>
      apiClient<{ job: Job; ok: boolean }>(`/jobs/${jobId}/refetch`, { method: 'POST', body: {} }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: workspaceKeys.bootstrap })
      void qc.invalidateQueries({ queryKey: jobKeys.detail(jobId) })
    },
  })
}

export function useAddJobMutation() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (jobData: { url: string; title: string; company: string; location: string; description: string }) =>
      apiClient<{ job: Job; created: boolean }>('/jobs', { method: 'POST', body: jobData }),
    onSuccess: (data) => {
      void qc.invalidateQueries({ queryKey: workspaceKeys.bootstrap })
      if (data.job?.id) {
        void qc.invalidateQueries({ queryKey: jobKeys.detail(data.job.id) })
      }
    },
  })
}

export function useImportJobMutation() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (params: { url: string }) =>
      apiClient<{ job: Job; created: boolean; run_id: string; ok: boolean }>('/jobs/import', {
        method: 'POST',
        body: params,
      }),
    onSuccess: (data) => {
      void qc.invalidateQueries({ queryKey: workspaceKeys.bootstrap })
      if (data.job?.id) {
        void qc.invalidateQueries({ queryKey: jobKeys.detail(data.job.id) })
      }
    },
  })
}

export function usePrepareJobMutation(jobId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (params: { mode: 'ai' | 'local' }) =>
      apiClient<{ run_id: string }>(`/jobs/${jobId}/prepare`, { method: 'POST', body: params }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: workspaceKeys.bootstrap })
      void qc.invalidateQueries({ queryKey: jobKeys.detail(jobId) })
    },
  })
}

export function useInspectJobMutation(jobId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: () =>
      apiClient<{ run_id: string }>(`/jobs/${jobId}/inspect`, { method: 'POST', body: {} }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: workspaceKeys.bootstrap })
      void qc.invalidateQueries({ queryKey: jobKeys.detail(jobId) })
    },
  })
}

export function useCoverLetterMutation(jobId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (params: { mode: 'ai' | 'local' }) =>
      apiClient<{ run_id: string }>(`/jobs/${jobId}/cover-letter`, { method: 'POST', body: params }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: workspaceKeys.bootstrap })
      void qc.invalidateQueries({ queryKey: jobKeys.detail(jobId) })
    },
  })
}

export function useReviewJobMutation(jobId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (payload: {
      package_hash: string
      cv_reviewed: boolean
      coverage_reviewed: boolean
      answers: Record<string, string>
      supports: ('full' | 'partial' | 'missing')[]
    }) => apiClient<{ ok: boolean }>(`/jobs/${jobId}/review`, { method: 'PUT', body: payload }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: workspaceKeys.bootstrap })
      void qc.invalidateQueries({ queryKey: jobKeys.detail(jobId) })
    },
  })
}

export function useApproveJobMutation(jobId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (params: { package_hash: string }) =>
      apiClient<{ ok: boolean }>(`/jobs/${jobId}/approve`, { method: 'POST', body: params }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: workspaceKeys.bootstrap })
      void qc.invalidateQueries({ queryKey: jobKeys.detail(jobId) })
    },
  })
}

export function useSubmitJobMutation(jobId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (params: { package_hash: string }) =>
      apiClient<{ ok: boolean }>(`/jobs/${jobId}/submit`, { method: 'POST', body: params }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: workspaceKeys.bootstrap })
      void qc.invalidateQueries({ queryKey: jobKeys.detail(jobId) })
    },
  })
}

export function useSkipJobMutation(jobId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: () => apiClient<{ ok: boolean }>(`/jobs/${jobId}/skip`, { method: 'POST', body: {} }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: workspaceKeys.bootstrap })
      void qc.invalidateQueries({ queryKey: jobKeys.detail(jobId) })
    },
  })
}

export function useResolveJobMutation(jobId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (payload: { status: 'submitted' | 'not_submitted'; note: string }) =>
      apiClient<{ ok: boolean }>(`/jobs/${jobId}/resolve`, { method: 'POST', body: payload }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: workspaceKeys.bootstrap })
      void qc.invalidateQueries({ queryKey: jobKeys.detail(jobId) })
    },
  })
}

export function useAutoApplyJobMutation(jobId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (params: { package_hash?: string; auto_submit: boolean; headless?: boolean }) =>
      apiClient<{ run_id: string }>(`/jobs/${jobId}/auto-apply`, { method: 'POST', body: params }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: workspaceKeys.bootstrap })
      void qc.invalidateQueries({ queryKey: jobKeys.detail(jobId) })
    },
  })
}

export function useOpenBrowserSessionMutation() {
  return useMutation({
    mutationFn: (params?: { url?: string }) =>
      apiClient<{ ok: boolean; message: string }>('/browser/open-session', {
        method: 'POST',
        body: { url: params?.url || 'https://www.linkedin.com' },
      }),
  })
}
