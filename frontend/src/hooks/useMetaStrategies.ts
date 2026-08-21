import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  fetchMetaStrategies,
  createMetaStrategy,
  fetchMetaStrategy,
  updateMetaStrategy,
  deleteMetaStrategy,
  addStrategyToMetaPool,
  removeStrategyFromMetaPool,
  fetchMetaRankings,
  evaluateMetaPromotion,
  forceMetaPromote,
  fetchMetaPerformance,
} from '@/lib/api'

export function useMetaStrategies() {
  return useQuery({
    queryKey: ['meta-strategies'],
    queryFn: () => fetchMetaStrategies(),
  })
}

export function useMetaStrategy(id: string) {
  return useQuery({
    queryKey: ['meta-strategy', id],
    queryFn: () => fetchMetaStrategy(id),
    enabled: !!id,
  })
}

export function useCreateMetaStrategy() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: createMetaStrategy,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['meta-strategies'] })
    },
  })
}

export function useUpdateMetaStrategy() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: any }) => updateMetaStrategy(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['meta-strategies'] })
    },
  })
}

export function useDeleteMetaStrategy() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: deleteMetaStrategy,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['meta-strategies'] })
    },
  })
}

export function useAddStrategyToMetaPool() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ msId, strategyId }: { msId: string; strategyId: string }) =>
      addStrategyToMetaPool(msId, strategyId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['meta-strategy'] })
      queryClient.invalidateQueries({ queryKey: ['meta-strategies'] })
    },
  })
}

export function useRemoveStrategyFromMetaPool() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ msId, strategyId }: { msId: string; strategyId: string }) =>
      removeStrategyFromMetaPool(msId, strategyId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['meta-strategy'] })
      queryClient.invalidateQueries({ queryKey: ['meta-strategies'] })
    },
  })
}

export function useMetaRankings(id: string) {
  return useQuery({
    queryKey: ['meta-rankings', id],
    queryFn: () => fetchMetaRankings(id),
    enabled: !!id,
    refetchInterval: 60_000,
  })
}

export function useEvaluateMetaPromotion() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: evaluateMetaPromotion,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['meta-rankings'] })
      queryClient.invalidateQueries({ queryKey: ['meta-strategy'] })
      queryClient.invalidateQueries({ queryKey: ['meta-strategies'] })
    },
  })
}

export function useMetaPerformance(id: string) {
  return useQuery({
    queryKey: ['meta-performance', id],
    queryFn: () => fetchMetaPerformance(id),
    enabled: !!id,
    refetchInterval: 120_000,
  })
}

export function useForceMetaPromote() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ msId, strategyId }: { msId: string; strategyId: string }) =>
      forceMetaPromote(msId, strategyId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['meta-rankings'] })
      queryClient.invalidateQueries({ queryKey: ['meta-strategy'] })
      queryClient.invalidateQueries({ queryKey: ['meta-strategies'] })
    },
  })
}
