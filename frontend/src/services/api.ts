/**
 * ARGUS REST API Service Layer
 */
import {
  MetricsResponse,
  MetricSnapshot,
  Incident,
  RecoveryOptionsResponse,
  ApprovalResponse,
  DiagnosisResponse,
  BenchmarkResult,
  HealthResponse,
} from '../types';

const BASE_URL = '';

async function fetchJson<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${endpoint}`, {
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
    ...options,
  });

  if (!res.ok) {
    let errorDetail = `Request failed: ${res.status} ${res.statusText}`;
    try {
      const errJson = await res.json();
      if (errJson.detail) errorDetail = errJson.detail;
    } catch {
      // ignore
    }
    throw new Error(errorDetail);
  }

  return res.json();
}

export const api = {
  // Metrics
  getMetrics: async (limit = 50): Promise<MetricsResponse> => {
    const data = await fetchJson<any>(`/api/metrics?limit=${limit}`);
    const normalize = (m: any = {}, timestamp?: string): MetricSnapshot => {
      const raw = m?.metrics || m || {};
      const tokenCount = Number(raw.token_count ?? raw.token_usage ?? 500);
      const hallucination = Number(raw.hallucination_score ?? 0.03);
      const answerRelevance = Number(raw.answer_relevance ?? Math.max(0, 1 - hallucination));
      const cpuRaw = Number(raw.cpu_utilization ?? raw.cpu_usage ?? 35);
      const cpuUtil = cpuRaw > 1 ? cpuRaw / 100 : cpuRaw;
      const cost = Number(raw.cost_per_query ?? (tokenCount * 0.00003));
      const loopCount = Number(raw.loop_count ?? 0);

      return {
        timestamp: raw.timestamp || m.timestamp || timestamp || new Date().toISOString(),
        latency: Number(raw.latency ?? 1.2),
        error_rate: Number(raw.error_rate ?? 0.005),
        token_count: tokenCount,
        token_usage: tokenCount,
        cost_per_query: cost,
        retrieval_score: Number(raw.retrieval_score ?? 0.92),
        answer_relevance: answerRelevance,
        tool_failure_rate: Number(raw.tool_failure_rate ?? 0.008),
        loop_count: loopCount,
        api_success_rate: Number(raw.api_success_rate ?? 0.995),
        cpu_utilization: cpuUtil,
        cpu_usage: cpuRaw > 1 ? cpuRaw : cpuRaw * 100,
        ...raw,
      };
    };

    const current = normalize(data.current);
    const history = (data.history || []).map((h: any) => normalize(h, h.timestamp));

    return {
      current,
      history,
      count: data.count || history.length,
    };
  },

  // Incidents
  getIncidents: (limit = 100): Promise<Incident[]> =>
    fetchJson<Incident[]>(`/api/incidents?limit=${limit}`),

  getIncident: (id: string): Promise<Incident> =>
    fetchJson<Incident>(`/api/incidents/${id}`),

  simulateIncident: (data: Partial<Incident>): Promise<Incident> =>
    fetchJson<Incident>('/api/incidents/simulate', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  analyzeIncident: (id: string): Promise<any> =>
    fetchJson<any>(`/api/incidents/${id}/analyze`, {
      method: 'POST',
    }),

  getDiagnosis: (id: string): Promise<DiagnosisResponse> =>
    fetchJson<DiagnosisResponse>(`/api/incidents/${id}/diagnosis`),

  getRecoveryOptions: (id: string): Promise<RecoveryOptionsResponse> =>
    fetchJson<RecoveryOptionsResponse>(`/api/incidents/${id}/recovery-options`),

  approveRecovery: (id: string, notes = 'Approved via Operator Dashboard'): Promise<ApprovalResponse> =>
    fetchJson<ApprovalResponse>(`/api/incidents/${id}/approve`, {
      method: 'POST',
      body: JSON.stringify({ actor: 'operator:engineer', notes }),
    }),

  rejectRecovery: (id: string, notes = 'Rejected by Operator — escalating'): Promise<ApprovalResponse> =>
    fetchJson<ApprovalResponse>(`/api/incidents/${id}/reject`, {
      method: 'POST',
      body: JSON.stringify({ actor: 'operator:engineer', notes }),
    }),

  getEvaluation: (id: string): Promise<any> =>
    fetchJson<any>(`/api/incidents/${id}/evaluation`),

  // Simulation
  injectFault: (faultType: string): Promise<any> =>
    fetchJson<any>('/api/simulation/inject', {
      method: 'POST',
      body: JSON.stringify({ fault_type: faultType }),
    }),

  resetSimulation: (): Promise<any> =>
    fetchJson<any>('/api/simulation/reset', {
      method: 'POST',
    }),

  runSection29Demo: (): Promise<any> =>
    fetchJson<any>('/api/simulation/demo', {
      method: 'POST',
    }),

  // Evaluation & Benchmark
  getBenchmark: (): Promise<BenchmarkResult> =>
    fetchJson<BenchmarkResult>('/api/evaluation/benchmark'),

  runBenchmark: (): Promise<any> =>
    fetchJson<any>('/api/evaluation/run', {
      method: 'POST',
    }),

  // Health
  getHealth: (): Promise<HealthResponse> =>
    fetchJson<HealthResponse>('/health'),
};
