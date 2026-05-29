import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiFetch } from '@/lib/auth'
import {
  SafeWallet,
  WithdrawalRecord,
  WithdrawalStrategy,
} from '@/types/withdrawal'

const queryKeys = {
  safeWallets: ['withdrawal', 'wallets'] as const,
  safeWalletBalance: (id: string) => ['withdrawal', 'balance', id] as const,
  withdrawalHistory: ['withdrawal', 'history'] as const,
  withdrawalStrategies: ['withdrawal', 'strategies'] as const,
}

export function useSafeWallets() {
  return useQuery<SafeWallet[]>({
    queryKey: queryKeys.safeWallets,
    queryFn: () => apiFetch('/api/withdrawal/wallets'),
  })
}

export function useCreateSafeWallet() {
  const queryClient = useQueryClient()
  return useMutation<SafeWallet, Error, { name: string; currency: string; address?: string }>({
    mutationFn: (data) =>
      apiFetch('/api/withdrawal/wallets', {
        method: 'POST',
        body: JSON.stringify(data),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.safeWallets })
    },
  })
}

export function useSafeWalletBalance(walletId: string | null) {
  return useQuery<{ balance: number; currency: string }, Error>({
    queryKey: walletId ? queryKeys.safeWalletBalance(walletId) : ['withdrawal', 'balance', 'none'],
    queryFn: () => apiFetch(`/api/withdrawal/balance?wallet_id=${walletId}`),
    enabled: !!walletId,
  })
}

export function useTransferToSafe() {
  const queryClient = useQueryClient()
  return useMutation<
    WithdrawalRecord,
    Error,
    { wallet_id: string; amount: number; source: string }
  >({
    mutationFn: (data) =>
      apiFetch('/api/withdrawal/transfer', {
        method: 'POST',
        body: JSON.stringify(data),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.safeWallets })
      queryClient.invalidateQueries({ queryKey: queryKeys.withdrawalHistory })
    },
  })
}

export function useWithdrawalHistory() {
  return useQuery<WithdrawalRecord[]>({
    queryKey: queryKeys.withdrawalHistory,
    queryFn: () => apiFetch('/api/withdrawal/history'),
  })
}

export function useWithdrawalStrategies() {
  return useQuery<WithdrawalStrategy[]>({
    queryKey: queryKeys.withdrawalStrategies,
    queryFn: () => apiFetch('/api/withdrawal/strategies'),
  })
}

export function useCreateWithdrawalStrategy() {
  const queryClient = useQueryClient()
  return useMutation<
    WithdrawalStrategy,
    Error,
    { name: string; description?: string; safe_wallet_id?: string; steps: WithdrawalStrategy['steps'] }
  >({
    mutationFn: (data) =>
      apiFetch('/api/withdrawal/strategies', {
        method: 'POST',
        body: JSON.stringify(data),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.withdrawalStrategies })
    },
  })
}

export function useUpdateWithdrawalStrategy() {
  const queryClient = useQueryClient()
  return useMutation<
    WithdrawalStrategy,
    Error,
    { id: string; data: Partial<WithdrawalStrategy> }
  >({
    mutationFn: ({ id, data }) =>
      apiFetch(`/api/withdrawal/strategies/${id}`, {
        method: 'PUT',
        body: JSON.stringify(data),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.withdrawalStrategies })
    },
  })
}

export function useDeleteWithdrawalStrategy() {
  const queryClient = useQueryClient()
  return useMutation<void, Error, string>({
    mutationFn: (id) =>
      apiFetch(`/api/withdrawal/strategies/${id}`, {
        method: 'DELETE',
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.withdrawalStrategies })
    },
  })
}

export function useEvaluateWithdrawalStrategy() {
  return useMutation<
    { triggered: boolean; steps_evaluated: number },
    Error,
    string
  >({
    mutationFn: (id) =>
      apiFetch(`/api/withdrawal/strategies/${id}/evaluate`, {
        method: 'POST',
      }),
  })
}

export function useToggleWithdrawalStrategy() {
  const queryClient = useQueryClient()
  return useMutation<
    WithdrawalStrategy,
    Error,
    string
  >({
    mutationFn: (id) =>
      apiFetch(`/api/withdrawal/strategies/${id}/toggle`, {
        method: 'POST',
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.withdrawalStrategies })
    },
  })
}
