import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiFetch } from '@/lib/auth'
import {
  SafeWallet,
  WithdrawalRecord,
  WithdrawalStrategy,
} from '@/types/withdrawal'

const queryKeys = {
  safeWallets: ['withdrawal', 'wallets'] as const,
  safeWalletBalance: ['withdrawal', 'balance'] as const,
  withdrawalHistory: ['withdrawal', 'history'] as const,
  withdrawalStrategies: ['withdrawal', 'strategies'] as const,
}

export function useSafeWallets() {
  return useQuery<SafeWallet[]>({
    queryKey: queryKeys.safeWallets,
    queryFn: async () => {
      const res = await apiFetch('/api/withdrawal/wallets')
      if (!res.ok) throw new Error('Failed to fetch wallets')
      return res.json()
    },
  })
}

export function useCreateSafeWallet() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (data: { name: string; currency: string }) => {
      const res = await apiFetch('/api/withdrawal/wallets', {
        method: 'POST',
        body: JSON.stringify(data),
      })
      if (!res.ok) throw new Error('Failed to create wallet')
      return res.json()
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.safeWallets })
    },
  })
}

export function useSafeWalletBalance() {
  return useQuery({
    queryKey: queryKeys.safeWalletBalance,
    queryFn: async () => {
      const res = await apiFetch('/api/withdrawal/balance')
      if (!res.ok) throw new Error('Failed to fetch balance')
      return res.json()
    },
  })
}

export function useTransferToSafe() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (data: { amount: number; currency: string; source: string }) => {
      const res = await apiFetch('/api/withdrawal/transfer', {
        method: 'POST',
        body: JSON.stringify(data),
      })
      if (!res.ok) throw new Error('Failed to transfer')
      return res.json()
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.safeWallets })
      queryClient.invalidateQueries({ queryKey: queryKeys.safeWalletBalance })
      queryClient.invalidateQueries({ queryKey: queryKeys.withdrawalHistory })
    },
  })
}

export function useWithdrawalHistory() {
  return useQuery<WithdrawalRecord[]>({
    queryKey: queryKeys.withdrawalHistory,
    queryFn: async () => {
      const res = await apiFetch('/api/withdrawal/history')
      if (!res.ok) throw new Error('Failed to fetch history')
      return res.json()
    },
  })
}

export function useWithdrawalStrategies() {
  return useQuery<WithdrawalStrategy[]>({
    queryKey: queryKeys.withdrawalStrategies,
    queryFn: async () => {
      const res = await apiFetch('/api/withdrawal/strategies')
      if (!res.ok) throw new Error('Failed to fetch strategies')
      return res.json()
    },
  })
}

export function useCreateWithdrawalStrategy() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (data: { name: string; description?: string; steps: WithdrawalStep[]; safe_wallet_id?: string }) => {
      const res = await apiFetch('/api/withdrawal/strategies', {
        method: 'POST',
        body: JSON.stringify(data),
      })
      if (!res.ok) throw new Error('Failed to create strategy')
      return res.json()
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.withdrawalStrategies })
    },
  })
}

export function useUpdateWithdrawalStrategy() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async ({ id, data }: { id: string; data: Partial<WithdrawalStrategy> }) => {
      const res = await apiFetch(`/api/withdrawal/strategies/${id}`, {
        method: 'PUT',
        body: JSON.stringify(data),
      })
      if (!res.ok) throw new Error('Failed to update strategy')
      return res.json()
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.withdrawalStrategies })
    },
  })
}

export function useDeleteWithdrawalStrategy() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (id: string) => {
      const res = await apiFetch(`/api/withdrawal/strategies/${id}`, {
        method: 'DELETE',
      })
      if (!res.ok) throw new Error('Failed to delete strategy')
      return res.json()
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.withdrawalStrategies })
    },
  })
}

export function useEvaluateWithdrawalStrategy() {
  return useMutation({
    mutationFn: async (id: string) => {
      const res = await apiFetch(`/api/withdrawal/strategies/${id}/evaluate`, {
        method: 'POST',
      })
      if (!res.ok) throw new Error('Failed to evaluate strategy')
      return res.json()
    },
  })
}

export function useToggleWithdrawalStrategy() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (id: string) => {
      const res = await apiFetch(`/api/withdrawal/strategies/${id}/toggle`, {
        method: 'POST',
      })
      if (!res.ok) throw new Error('Failed to toggle strategy')
      return res.json()
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.withdrawalStrategies })
    },
  })
}
