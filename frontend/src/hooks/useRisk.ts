import { useQuery } from '@tanstack/react-query'
import { fetchRiskSummary, fetchVaR, fetchCorrelation, fetchDrawdown, fetchPortfolioRisk } from '@/lib/api'

export function useRiskSummary() {
  return useQuery({
    queryKey: ['risk-summary'],
    queryFn: fetchRiskSummary,
    refetchInterval: 30_000,
  })
}

export function useVaR(confidence = 0.95) {
  return useQuery({
    queryKey: ['risk-var', confidence],
    queryFn: () => fetchVaR(confidence),
    refetchInterval: 60_000,
  })
}

export function useCorrelation() {
  return useQuery({
    queryKey: ['risk-correlation'],
    queryFn: fetchCorrelation,
    refetchInterval: 60_000,
  })
}

export function useDrawdown() {
  return useQuery({
    queryKey: ['risk-drawdown'],
    queryFn: fetchDrawdown,
    refetchInterval: 30_000,
  })
}

export function usePortfolioRisk() {
  return useQuery({
    queryKey: ['risk-portfolio'],
    queryFn: fetchPortfolioRisk,
    refetchInterval: 30_000,
  })
}
