import { apiClient, type ApiEnvelope } from '@/api/client'

export interface EvaluationPayload { tester_code: string; profile_scenario: string; recommendation_set_id: string; relevance_score: number; difficulty_score: number; reason_score: number; holding_score: number; satisfaction_score: number; notes: string | null }
export interface EvaluationSummaryData { sample_size: number; averages: { relevance: number; difficulty: number; reason: number; holding: number; satisfaction: number }; satisfaction_distribution: Record<string, number>; scenario_counts: Record<string, number> }
export async function createEvaluation(payload: EvaluationPayload) { return (await apiClient.post('/evaluations', payload)).data }
export async function getEvaluationSummary() { return (await apiClient.get<ApiEnvelope<EvaluationSummaryData>>('/admin/evaluations/summary')).data.data }
