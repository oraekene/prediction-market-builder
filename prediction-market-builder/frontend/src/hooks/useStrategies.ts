import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  fetchStrategies, fetchStrategy, createStrategy, updateStrategy, deleteStrategy,
  deployStrategy, pauseStrategy, resumeStrategy, archiveStrategy, rollbackStrategy,
  fetchStrategyHistory, evaluateStrategyData,
  fetchStrategyTemplates, createStrategyTemplate, fetchStrategyTemplate,
  updateStrategyTemplate, deleteStrategyTemplate, applyStrategyTemplate,
} from '@/lib/api'

export function useStrategies() {
  return useQuery({
    queryKey: ['strategies'],
    queryFn: fetchStrategies,
  })
}

export function useStrategy(id: string) {
  return useQuery({
    queryKey: ['strategy', id],
    queryFn: () => fetchStrategy(id),
    enabled: !!id,
  })
}

export function useCreateStrategy() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: createStrategy,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['strategies'] })
    },
  })
}

export function useUpdateStrategy() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: any }) => updateStrategy(id, data),
    onSuccess: (_, { id }) => {
      queryClient.invalidateQueries({ queryKey: ['strategies'] })
      queryClient.invalidateQueries({ queryKey: ['strategy', id] })
    },
  })
}

export function useDeleteStrategy() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: deleteStrategy,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['strategies'] })
    },
  })
}

export function useDeployStrategy() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: deployStrategy,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['strategies'] })
    },
  })
}

export function usePauseStrategy() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: pauseStrategy,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['strategies'] })
    },
  })
}

export function useResumeStrategy() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: resumeStrategy,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['strategies'] })
    },
  })
}

export function useArchiveStrategy() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: archiveStrategy,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['strategies'] })
    },
  })
}

export function useRollbackStrategy() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: rollbackStrategy,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['strategies'] })
    },
  })
}

export function useStrategyHistory(id: string) {
  return useQuery({
    queryKey: ['strategy', id, 'history'],
    queryFn: () => fetchStrategyHistory(id),
    enabled: !!id,
  })
}

export function useEvaluateStrategyData() {
  return useMutation({
    mutationFn: evaluateStrategyData,
  })
}

export function useStrategyTemplates() {
  return useQuery({
    queryKey: ['strategy-templates'],
    queryFn: fetchStrategyTemplates,
  })
}

export function useStrategyTemplate(id: string) {
  return useQuery({
    queryKey: ['strategy-template', id],
    queryFn: () => fetchStrategyTemplate(id),
    enabled: !!id,
  })
}

export function useCreateStrategyTemplate() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: createStrategyTemplate,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['strategy-templates'] })
    },
  })
}

export function useUpdateStrategyTemplate() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: any }) => updateStrategyTemplate(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['strategy-templates'] })
    },
  })
}

export function useDeleteStrategyTemplate() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: deleteStrategyTemplate,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['strategy-templates'] })
    },
  })
}

export function useApplyStrategyTemplate() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: applyStrategyTemplate,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['strategy-templates'] })
      queryClient.invalidateQueries({ queryKey: ['strategies'] })
    },
  })
}
