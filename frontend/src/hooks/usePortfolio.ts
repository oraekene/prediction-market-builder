import { useQuery } from '@tanstack/react-query'
import { fetchPortfolio } from '@/lib/api'

export function usePortfolio() {
  return useQuery({
    queryKey: ['portfolio'],
    queryFn: fetchPortfolio,
    refetchInterval: 60_000,
  })
}
