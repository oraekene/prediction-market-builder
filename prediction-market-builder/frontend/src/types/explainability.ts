export interface ShapContribution {
  name: string
  shap_value: number
  feature_value: number
}

export interface ShapExplanation {
  base_value: number
  output_value: number
  contributions: ShapContribution[]
  mean_abs_importance: Record<string, number>
  ranking: string[]
}

export interface ShapSummary {
  base_value: number | null
  output_value: number | null
  top_features: ShapContribution[]
}

export interface ShapAggregate {
  mean_abs_importance: Record<string, number>
  ranking: string[]
}

export interface ShapExplainResponse {
  explanation: ShapExplanation | null
  message?: string
}

export interface ShapAggregateResponse {
  aggregate: ShapAggregate | null
  count: number
}
