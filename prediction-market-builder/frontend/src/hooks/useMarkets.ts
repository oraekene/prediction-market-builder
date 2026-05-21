import { useQuery } from '@tanstack/react-query'
import { fetchMarkets } from '@/lib/api'

export function useMarkets(params?: Record<string, string>) {
  return useQuery({
    queryKey: ['markets', params],
    queryFn: () => fetchMarkets(params),
    refetchInterval: 30_000,
  })
}

export function useMarket(id: string) {
  return useQuery({
    queryKey: ['market', id],
    queryFn: () => fetch(`/api/markets/${id}`).then(r => r.json()),
    enabled: !!id,
  })
}
