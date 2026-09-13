import React, { useState, useEffect } from 'react';
import {
  Activity,
  AlertTriangle,
  ArrowRight,
  CheckCircle,
  Clock,
  Coins,
  Cpu,
  Database,
  Flame,
  Layers,
  Play,
  RefreshCw,
  Repeat,
  Shield,
  ShieldAlert,
  Zap,
} from 'lucide-react';
import { api } from '../services/api';
import { MetricSnapshot } from '../types';

interface FaultTypeConfig {
  id: string;
  name: string;
  category: string;
  description: string;
  impactMetrics: string[];
  severity: 'critical' | 'high' | 'medium';
  icon: any;
}

export const SimulationPage: React.FC = () => {
  const [currentMetrics, setCurrentMetrics] = useState<MetricSnapshot | null>(null);
  const [activeFault, setActiveFault] = useState<string | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [demoRunning, setDemoRunning] = useState<boolean>(false);
  const [demoStep, setDemoStep] = useState<string | null>(null);

  const faultConfigs: FaultTypeConfig[] = [
    {
      id: 'LATENCY_SPIKE',
      name: 'Event Loop Latency Spike',
      category: 'Performance',
      description: 'Synchronous blocking calls stall async event loops and downstream microservices.',
      impactMetrics: ['latency > 2.8s', 'cpu_utilization > 85%'],
      severity: 'high',
      icon: Clock,
    },
    {
      id: 'LLM_FAILURE',
      name: 'Model Provider 500s & Timeouts',
      category: 'Inference',
      description: 'Upstream LLM provider HTTP 500s, token timeouts, and schema truncation.',
      impactMetrics: ['error_rate > 8%', 'api_success_rate < 90%'],
      severity: 'critical',
      icon: AlertTriangle,
    },
    {
      id: 'RAG_DEGRADATION',
      name: 'Vector Embedding Drift & Hallucination',
      category: 'Retrieval',
      description: 'Incompatible embedding models and chunk fragmentation leading to low relevance.',
      impactMetrics: ['retrieval_score < 0.65', 'answer_relevance < 0.70'],
      severity: 'high',
      icon: Database,
    },
    {
      id: 'TOOL_FAILURE',
      name: 'MCP Tool Parameter & Rate Limit Cascade',
      category: 'Tools / MCP',
      description: 'Schema parameter mismatches and upstream API rate limit throttling.',
      impactMetrics: ['tool_failure_rate > 7%', 'error_rate > 4%'],
      severity: 'medium',
      icon: Zap,
    },
    {
      id: 'COST_SPIKE',
      name: 'Runaway Token Explosion',
      category: 'FinOps',
      description: 'Recursive prompt chains and unbounded conversational context accumulation.',
      impactMetrics: ['token_count > 2500', 'cost_per_query > $0.09'],
      severity: 'high',
      icon: Coins,
    },
    {
      id: 'AGENT_LOOP',
      name: 'ReAct Circular Reflection Stagnation',
      category: 'Agents',
      description: 'Agent repeating identical tool execution in infinite circular reasoning cycles.',
      impactMetrics: ['loop_count > 3', 'latency > 3.0s'],
      severity: 'high',
      icon: Repeat,
    },
  ];

  const isMountedRef = React.useRef(true);

  const fetchMetrics = async () => {
    try {
      const [data, statusData] = await Promise.all([
        api.getMetrics(5),
        api.getSimulationStatus().catch(() => null),
      ]);
      if (!isMountedRef.current) return;
      setCurrentMetrics(data.current);
      if (statusData) {
        if (statusData.is_fault_active && statusData.active_fault) {
          setActiveFault(statusData.active_fault);
        } else if (!statusData.is_fault_active && activeFault && !statusMessage?.includes('Fault injected')) {
          setActiveFault(null);
        }
      }
    } catch (e) {
      if (isMountedRef.current) {
        console.error(e);
      }
    }
  };

  useEffect(() => {
    isMountedRef.current = true;
    fetchMetrics();
    const timer = setInterval(() => {
      if (isMountedRef.current) {
        fetchMetrics();
      }
    }, 2000);
    return () => {
      isMountedRef.current = false;
      clearInterval(timer);
    };
  }, []);

  const handleInjectFault = async (faultId: string) => {
    setLoading(true);
    setStatusMessage(null);
    try {
      await api.injectFault(faultId);
      setActiveFault(faultId);
      setStatusMessage(`Fault injected: ${faultId}. Live telemetry stream is now reflecting anomalous breach.`);
      await fetchMetrics();
    } catch (e: any) {
      alert(`Fault injection failed: ${e.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleReset = async () => {
    setLoading(true);
    setStatusMessage(null);
    try {
      await api.resetSimulation();
      setActiveFault(null);
      setStatusMessage('Simulation reset to normal healthy baseline.');
      await fetchMetrics();
    } catch (e: any) {
      alert(`Reset failed: ${e.message}`);
    } finally {
      setLoading(false);
    }
  };

  const [demoStepsList, setDemoStepsList] = useState<any[]>([]);
  const [demoIncidentId, setDemoIncidentId] = useState<string | null>(null);

  // Section 29 End-to-End Demo Runner
  const handleRunDemo = async () => {
    setDemoRunning(true);
    setDemoStepsList([]);
    setDemoIncidentId(null);
    setDemoStep('Initializing Section 29 14-Step Autonomous Reliability Demonstration...');

    try {
      const res = await api.runSection29Demo();
      setDemoStepsList(res.steps || []);
      setDemoIncidentId(res.incident_id || null);
      setActiveFault(null);
      setStatusMessage(
        `Section 29 Demo Completed! Incident ${res.incident_id?.slice(0, 8)} executed all 14 steps: anomaly detection, root cause diagnosis, runbook retrieval, counterfactual simulation, human approval, MCP recovery, SLA verification, evaluation, and postmortem learning.`
      );
      await fetchMetrics();
    } catch (e: any) {
      alert(`Demo encountered error: ${e.message}`);
    } finally {
      setDemoRunning(false);
      setDemoStep(null);
    }
  };

  const cur: any = currentMetrics || {
    latency: 1.1,
    error_rate: 0.005,
    retrieval_score: 0.92,
    tool_failure_rate: 0.01,
    cost_per_query: 0.02,
    loop_count: 0,
    hallucination_score: 0.03,
    answer_relevance: 0.92,
    api_success_rate: 0.995,
    token_usage: 500,
    token_count: 500,
    cpu_usage: 35,
    cpu_utilization: 0.35,
  };

  // Complete SLA threshold evaluation matching the metric cards & canonical fault signatures
  const isLatencyBreach = (cur.latency ?? 0) > 2.2;
  const isErrorRateBreach = (cur.error_rate ?? 0) > 0.02;
  const isRetrievalBreach = (cur.retrieval_score ?? 1) < 0.85;
  const isToolFailureBreach = (cur.tool_failure_rate ?? 0) > 0.03;
  const isCostBreach = (cur.cost_per_query ?? 0) > 0.05;
  const isHallucinationBreach = (cur.hallucination_score ?? 0) > 0.05 || (cur.answer_relevance !== undefined && cur.answer_relevance < 0.88);
  const isLoopBreach = (cur.loop_count ?? 0) > 1;
  const isApiSuccessBreach = cur.api_success_rate !== undefined && cur.api_success_rate < 0.98;
  const isTokenBreach = (cur.token_usage ?? cur.token_count ?? 0) > 1500;
  const isCpuBreach = (cur.cpu_usage ?? 0) > 60 || (cur.cpu_utilization ?? 0) > 0.60;

  const breachedMetrics: string[] = [];
  if (isRetrievalBreach) breachedMetrics.push('RAG Retrieval');
  if (isLatencyBreach) breachedMetrics.push('Latency');
  if (isErrorRateBreach) breachedMetrics.push('Error Rate');
  if (isToolFailureBreach) breachedMetrics.push('Tool Failure');
  if (isCostBreach) breachedMetrics.push('Cost/Query');
  if (isHallucinationBreach) breachedMetrics.push('Hallucination');
  if (isLoopBreach) breachedMetrics.push('Agent Loop');
  if (isApiSuccessBreach) breachedMetrics.push('API Success');
  if (isTokenBreach) breachedMetrics.push('Token Explosion');
  if (isCpuBreach) breachedMetrics.push('CPU Load');

  const isDegraded = Boolean(activeFault) || breachedMetrics.length > 0;

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">Failure Simulation & Fault Injection Control</h1>
          <p className="page-desc">
            Direct telemetry manipulation and fault injection triggers wired to <code className="mono">POST /api/simulation/inject</code> per Section 24 & 29.
          </p>
        </div>

        <div style={{ display: 'flex', gap: '10px' }}>
          <button
            className="btn btn-secondary btn-sm"
            onClick={handleReset}
            disabled={loading || demoRunning}
          >
            <RefreshCw size={13} className={loading ? 'spin' : ''} />
            Reset to Normal
          </button>

          <button
            className="btn btn-primary btn-sm"
            onClick={handleRunDemo}
            disabled={demoRunning || loading}
          >
            <Play size={13} />
            {demoRunning ? 'Running ARGUS Demo...' : 'Run ARGUS Demo (Section 29)'}
          </button>
        </div>
      </div>

      {statusMessage && (
        <div
          style={{
            background: 'var(--status-pass-bg)',
            border: '1px solid var(--status-pass-border)',
            padding: '12px 16px',
            borderRadius: 'var(--radius-sm)',
            marginBottom: '20px',
            color: '#34d399',
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
          }}
        >
          <CheckCircle size={16} />
          <span>{statusMessage}</span>
        </div>
      )}

      {demoStep && (
        <div
          style={{
            background: 'rgba(59, 130, 246, 0.12)',
            border: '1px solid rgba(59, 130, 246, 0.35)',
            padding: '14px 18px',
            borderRadius: 'var(--radius-sm)',
            marginBottom: '20px',
            color: '#60a5fa',
            display: 'flex',
            alignItems: 'center',
            gap: '10px',
            fontWeight: 600,
          }}
        >
          <Activity size={18} className="spin" />
          <span>{demoStep}</span>
        </div>
      )}

      {/* Live Stream Telemetry Banner */}
      <div
        className="card"
        style={{
          marginBottom: '24px',
          borderColor: isDegraded ? '#ef4444' : '#10b981',
          background: isDegraded
            ? 'linear-gradient(180deg, var(--bg-surface) 0%, rgba(239, 68, 68, 0.06) 100%)'
            : 'var(--bg-surface)',
          boxShadow: isDegraded ? '0 0 15px rgba(239, 68, 68, 0.15)' : 'none',
        }}
      >
        <div className="card-header" style={{ borderBottom: 'none', paddingBottom: '0' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <span
              style={{
                width: '10px',
                height: '10px',
                borderRadius: '50%',
                background: isDegraded ? '#ef4444' : '#10b981',
                boxShadow: isDegraded ? '0 0 8px #ef4444' : '0 0 8px #10b981',
              }}
            ></span>
            <h3 className="card-title">
              Live Stream Status:{' '}
              {activeFault
                ? `FAULT ACTIVE (${activeFault})`
                : isDegraded
                ? `DEGRADED (${breachedMetrics.join(', ')} SLA Breach)`
                : 'HEALTHY BASELINE'}
            </h3>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            {isDegraded && (
              <span className="badge badge-critical" style={{ fontSize: '11px', fontWeight: 600 }}>
                DEGRADED
              </span>
            )}
            <span className="mono" style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
              Polling every 2s
            </span>
          </div>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: '12px', marginTop: '16px' }}>
          <div style={{
            background: 'var(--bg-canvas)',
            padding: '10px',
            borderRadius: 'var(--radius-sm)',
            border: isLatencyBreach ? '1px solid rgba(239, 68, 68, 0.4)' : '1px solid transparent',
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Latency</span>
              <span style={{ fontSize: '10px', color: isLatencyBreach ? '#f87171' : 'var(--text-muted)' }}>SLA &le; 2.2s</span>
            </div>
            <div className="mono" style={{ fontSize: '16px', fontWeight: 700, color: isLatencyBreach ? '#f87171' : '#f1f5f9' }}>
              {(cur.latency ?? 0).toFixed(2)}s
            </div>
          </div>

          <div style={{
            background: 'var(--bg-canvas)',
            padding: '10px',
            borderRadius: 'var(--radius-sm)',
            border: isErrorRateBreach ? '1px solid rgba(239, 68, 68, 0.4)' : '1px solid transparent',
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Error Rate</span>
              <span style={{ fontSize: '10px', color: isErrorRateBreach ? '#f87171' : 'var(--text-muted)' }}>SLA &le; 2.0%</span>
            </div>
            <div className="mono" style={{ fontSize: '16px', fontWeight: 700, color: isErrorRateBreach ? '#f87171' : '#f1f5f9' }}>
              {((cur.error_rate ?? 0) * 100).toFixed(1)}%
            </div>
          </div>

          <div style={{
            background: 'var(--bg-canvas)',
            padding: '10px',
            borderRadius: 'var(--radius-sm)',
            border: isRetrievalBreach ? '1px solid rgba(239, 68, 68, 0.4)' : '1px solid transparent',
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>RAG Retrieval</span>
              <span style={{ fontSize: '10px', color: isRetrievalBreach ? '#f87171' : 'var(--text-muted)' }}>SLA &ge; 0.850</span>
            </div>
            <div className="mono" style={{ fontSize: '16px', fontWeight: 700, color: isRetrievalBreach ? '#f87171' : '#f1f5f9' }}>
              {(cur.retrieval_score ?? 0).toFixed(3)}
            </div>
          </div>

          <div style={{
            background: 'var(--bg-canvas)',
            padding: '10px',
            borderRadius: 'var(--radius-sm)',
            border: isToolFailureBreach ? '1px solid rgba(239, 68, 68, 0.4)' : '1px solid transparent',
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Tool Failure</span>
              <span style={{ fontSize: '10px', color: isToolFailureBreach ? '#f87171' : 'var(--text-muted)' }}>SLA &le; 3.0%</span>
            </div>
            <div className="mono" style={{ fontSize: '16px', fontWeight: 700, color: isToolFailureBreach ? '#f87171' : '#f1f5f9' }}>
              {((cur.tool_failure_rate ?? 0) * 100).toFixed(1)}%
            </div>
          </div>

          <div style={{
            background: 'var(--bg-canvas)',
            padding: '10px',
            borderRadius: 'var(--radius-sm)',
            border: isCostBreach ? '1px solid rgba(239, 68, 68, 0.4)' : '1px solid transparent',
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Cost / Query</span>
              <span style={{ fontSize: '10px', color: isCostBreach ? '#f87171' : 'var(--text-muted)' }}>SLA &le; $0.050</span>
            </div>
            <div className="mono" style={{ fontSize: '16px', fontWeight: 700, color: isCostBreach ? '#f87171' : '#f1f5f9' }}>
              ${(cur.cost_per_query ?? 0).toFixed(3)}
            </div>
          </div>
        </div>
      </div>

      {/* 6 Fault Injection Cards Grid */}
      <h2 style={{ fontSize: '16px', fontWeight: 700, marginBottom: '14px', color: 'var(--text-primary)' }}>
        Canonical Failure Categories (Phase 2 Ingestion)
      </h2>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(340px, 1fr))', gap: '16px' }}>
        {faultConfigs.map((f) => {
          const IconComponent = f.icon;
          const isThisActive = activeFault === f.id;

          return (
            <div
              key={f.id}
              className="card"
              style={{
                display: 'flex',
                flexDirection: 'column',
                justifyContent: 'space-between',
                borderColor: isThisActive ? '#ef4444' : 'var(--border-subtle)',
                background: isThisActive ? 'rgba(239, 68, 68, 0.05)' : 'var(--bg-surface)',
              }}
            >
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '10px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <div
                      style={{
                        padding: '6px',
                        background: 'rgba(59, 130, 246, 0.12)',
                        borderRadius: 'var(--radius-sm)',
                        color: '#60a5fa',
                      }}
                    >
                      <IconComponent size={18} />
                    </div>
                    <div>
                      <div style={{ fontWeight: 600, fontSize: '14px', color: '#fff' }}>{f.name}</div>
                      <div className="mono" style={{ fontSize: '11px', color: 'var(--text-muted)' }}>{f.id}</div>
                    </div>
                  </div>
                  <span className={`badge ${f.severity === 'critical' ? 'badge-critical' : 'badge-high'}`}>
                    {f.severity.toUpperCase()}
                  </span>
                </div>

                <p style={{ fontSize: '12px', color: 'var(--text-secondary)', lineHeight: 1.5, marginBottom: '12px' }}>
                  {f.description}
                </p>

                <div style={{ marginBottom: '14px' }}>
                  <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginBottom: '4px' }}>
                    Breached SLA Signatures:
                  </div>
                  <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
                    {f.impactMetrics.map((m, idx) => (
                      <span key={idx} className="mono" style={{ fontSize: '11px', background: 'var(--bg-canvas)', padding: '2px 8px', borderRadius: '3px', color: '#f87171' }}>
                        {m}
                      </span>
                    ))}
                  </div>
                </div>
              </div>

              <div>
                <button
                  className="btn btn-danger btn-sm"
                  style={{ width: '100%' }}
                  onClick={() => handleInjectFault(f.id)}
                  disabled={loading || demoRunning}
                >
                  <Flame size={13} />
                  Inject {f.id}
                </button>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
