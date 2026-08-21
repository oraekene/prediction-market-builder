import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  fetchPaperWallet,
  resetPaperWallet,
  placePaperOrder,
  fetchPaperOrders,
  cancelPaperOrder,
  fetchPaperPerformance,
  comparePaperStrategies,
  syncPaperResolutions,
  fetchPaperMetric,
} from '@/lib/api_paper'

export function usePaperWallet(userId = 'default') {
  return useQuery({
    queryKey: ['paper-wallet', userId],
    queryFn: () => fetchPaperWallet(userId),
    refetchInterval: 30_000,
  })
}

export function useResetWallet() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (userId: string) => resetPaperWallet(userId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['paper-wallet'] })
      queryClient.invalidateQueries({ queryKey: ['paper-orders'] })
      queryClient.invalidateQueries({ queryKey: ['paper-performance'] })
    },
  })
}

export function usePlacePaperOrder() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: placePaperOrder,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['paper-wallet'] })
      queryClient.invalidateQueries({ queryKey: ['paper-orders'] })
      queryClient.invalidateQueries({ queryKey: ['paper-performance'] })
    },
  })
}

export function usePaperOrders(walletId?: string, status?: string) {
  return useQuery({
    queryKey: ['paper-orders', walletId, status],
    queryFn: () => fetchPaperOrders(walletId, status),
  })
}

export function useCancelPaperOrder() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: cancelPaperOrder,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['paper-wallet'] })
      queryClient.invalidateQueries({ queryKey: ['paper-orders'] })
    },
  })
}

export function usePaperPerformance(strategyId?: string, userId = 'default') {
  return useQuery({
    queryKey: ['paper-performance', strategyId, userId],
    queryFn: () => fetchPaperPerformance(strategyId, userId),
    refetchInterval: 30_000,
  })
}

export function useSyncResolutions() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: syncPaperResolutions,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['paper-wallet'] })
      queryClient.invalidateQueries({ queryKey: ['paper-orders'] })
      queryClient.invalidateQueries({ queryKey: ['paper-performance'] })
    },
  })
}

export function usePaperMetric(metric: string, window = 0, userId = 'default') {
  return useQuery({
    queryKey: ['paper-metric', metric, window, userId],
    queryFn: () => fetchPaperMetric(metric, window, userId),
    enabled: false,
  })
}

export function useCompareStrategies(strategyIds: string[]) {
  return useQuery({
    queryKey: ['paper-compare', strategyIds],
    queryFn: () => comparePaperStrategies(strategyIds),
    enabled: strategyIds.length >= 2,
  })
}
