/**
 * ARGUS REST API Service Layer
 */
import {
  MetricsResponse,
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
  getMetrics: (limit = 50): Promise<MetricsResponse> =>
    fetchJson<MetricsResponse>(`/api/metrics?limit=${limit}`),

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
