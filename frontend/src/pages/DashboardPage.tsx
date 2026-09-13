import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import {
  Activity,
  AlertCircle,
  Clock,
  Coins,
  Cpu,
  Database,
  ExternalLink,
  Flame,
  Layers,
  Play,
  Repeat,
  ShieldAlert,
  Zap,
  CheckCircle,
  ChevronRight,
  RefreshCw,
} from 'lucide-react';
import { api } from '../services/api';
import { MetricSnapshot, Incident } from '../types';
import { MetricCard } from '../components/MetricCard';
import { StatusBadge } from '../components/StatusBadge';

export const DashboardPage: React.FC = () => {
  const [currentMetrics, setCurrentMetrics] = useState<MetricSnapshot | null>(null);
  const [history, setHistory] = useState<MetricSnapshot[]>([]);
  const [recentIncidents, setRecentIncidents] = useState<Incident[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Section 29 14-Step One-Click Demo state
  const [demoRunning, setDemoRunning] = useState<boolean>(false);
  const [demoActiveStep, setDemoActiveStep] = useState<number | null>(null);
  const [demoStepsList, setDemoStepsList] = useState<any[]>([]);
  const [demoIncidentId, setDemoIncidentId] = useState<string | null>(null);
  const [demoStatusMessage, setDemoStatusMessage] = useState<string | null>(null);

  const handleRunSection29Demo = async () => {
    setDemoRunning(true);
    setDemoActiveStep(1);
    setDemoStepsList([]);
    setDemoIncidentId(null);
    setDemoStatusMessage('Starting Section 29 autonomous demonstration...');

    try {
      const res = await api.runSection29Demo();
      setDemoStepsList(res.steps || []);
      setDemoIncidentId(res.incident_id || null);
      setDemoActiveStep(14);
      setDemoStatusMessage(
        `Section 29 Demo completed successfully! Incident ${res.incident_id?.slice(0, 8)} created, diagnosed, recovered via MCP, verified, and learned.`
      );
      await loadData();
    } catch (err: any) {
      setDemoStatusMessage(`Demo encountered an error: ${err.message}`);
    } finally {
      setDemoRunning(false);
    }
  };

  const isMountedRef = React.useRef(true);

  const loadData = async () => {
    try {
      const [mRes, iRes] = await Promise.all([
        api.getMetrics(40),
        api.getIncidents(10),
      ]);
      if (!isMountedRef.current) return;
      setCurrentMetrics(mRes.current);
      setHistory(mRes.history || []);
      setRecentIncidents(iRes || []);
      setError(null);
    } catch (err: any) {
      if (isMountedRef.current) {
        setError(err.message || 'Failed to fetch dashboard metrics');
      }
    } finally {
      if (isMountedRef.current) {
        setLoading(false);
      }
    }
  };

  useEffect(() => {
    isMountedRef.current = true;
    loadData();
    const interval = setInterval(() => {
      if (isMountedRef.current) {
        loadData();
      }
    }, 2000);
    return () => {
      isMountedRef.current = false;
      clearInterval(interval);
    };
  }, []);

  if (loading && !currentMetrics) {
    return (
      <div style={{ padding: '64px', textAlign: 'center', color: 'var(--text-muted)' }}>
        <Activity size={32} style={{ animation: 'pulse 1s infinite', margin: '0 auto 16px' }} />
        <p>Connecting to ARGUS Telemetry Pipeline...</p>
      </div>
    );
  }

  const cur = currentMetrics || {
    latency: 0,
    error_rate: 0,
    token_count: 0,
    cost_per_query: 0,
    retrieval_score: 0,
    answer_relevance: 0,
    tool_failure_rate: 0,
    loop_count: 0,
    api_success_rate: 1.0,
    cpu_utilization: 0,
    timestamp: new Date().toISOString(),
  };

  const getMetricHistory = (key: keyof MetricSnapshot): number[] => {
    return history.map((h: any) => {
      const val = h[key] ?? h?.metrics?.[key as string];
      return Number(val) || 0;
    });
  };

  // Render SVG multi-series trend line chart
  const renderTrendChart = () => {
    if (history.length < 2) return null;
    const width = 800;
    const height = 180;
    const latVals = history.map((h: any) => Number(h.latency ?? h?.metrics?.latency ?? 0));
    const maxLat = Math.max(...latVals, 4.0);

    const latPoints = history
      .map((h: any, i) => {
        const x = (i / (history.length - 1)) * width;
        const lat = Number(h.latency ?? h?.metrics?.latency ?? 0);
        const y = height - (lat / maxLat) * (height - 30) - 15;
        return `${(x || 0).toFixed(1)},${(isNaN(y) ? 0 : y).toFixed(1)}`;
      })
      .join(' ');

    const errPoints = history
      .map((h: any, i) => {
        const x = (i / (history.length - 1)) * width;
        const err = Number(h.error_rate ?? h?.metrics?.error_rate ?? 0);
        const y = height - (err / 0.25) * (height - 30) - 15;
        return `${(x || 0).toFixed(1)},${(isNaN(y) ? 0 : y).toFixed(1)}`;
      })
      .join(' ');

    return (
      <div style={{ position: 'relative', width: '100%', overflow: 'hidden' }}>
        <svg viewBox={`0 0 ${width} ${height}`} style={{ width: '100%', height: '180px' }}>
          {/* Grid lines */}
          <line x1="0" y1={height - 15} x2={width} y2={height - 15} stroke="#1c2742" strokeWidth="1" />
          <line x1="0" y1={height / 2} x2={width} y2={height / 2} stroke="#1c2742" strokeWidth="1" strokeDasharray="4 4" />
          <line x1="0" y1="15" x2={width} y2="15" stroke="#1c2742" strokeWidth="1" strokeDasharray="4 4" />

          {/* Latency line (Blue) */}
          <polyline fill="none" stroke="#3b82f6" strokeWidth="2.5" points={latPoints} />

          {/* Error Rate line (Red) */}
          <polyline fill="none" stroke="#ef4444" strokeWidth="2" strokeDasharray="3 3" points={errPoints} />
        </svg>

        <div style={{ display: 'flex', gap: '20px', marginTop: '8px', fontSize: '11px', color: 'var(--text-muted)' }}>
          <span style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <span style={{ width: '10px', height: '3px', background: '#3b82f6', display: 'inline-block' }}></span>
            Latency (sec)
          </span>
          <span style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <span style={{ width: '10px', height: '2px', background: '#ef4444', display: 'inline-block' }}></span>
            Error Rate (%)
          </span>
        </div>
      </div>
    );
  };

  const isAnyBreached =
    cur.latency > 2.2 ||
    cur.error_rate > 0.02 ||
    cur.retrieval_score < 0.85 ||
    cur.tool_failure_rate > 0.03;

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">Operational Health & Telemetry</h1>
          <p className="page-desc">
            Real-time multi-agent observability pipeline monitoring AI application performance and SLA bounds.
          </p>
        </div>
        <div style={{ display: 'flex', gap: '12px' }}>
          <button
            className="btn btn-primary btn-sm"
            onClick={handleRunSection29Demo}
            disabled={demoRunning}
            style={{
              background: 'linear-gradient(135deg, #2563eb, #7c3aed)',
              border: 'none',
              boxShadow: '0 0 12px rgba(124, 58, 237, 0.4)',
            }}
          >
            <Play size={14} className={demoRunning ? 'spin' : ''} />
            {demoRunning ? 'Running Section 29 Demo...' : 'Run ARGUS Demo (Section 29)'}
          </button>
          <Link to="/simulation" className="btn btn-secondary btn-sm">
            <Flame size={14} />
            Inject Fault
          </Link>
          <Link to="/evaluation" className="btn btn-secondary btn-sm">
            <Activity size={14} />
            Benchmark
          </Link>
        </div>
      </div>

      {/* Section 29 Interactive 14-Step Timeline Card */}
      {(demoRunning || demoStepsList.length > 0) && (
        <div
          className="card"
          style={{
            marginBottom: '24px',
            border: '1px solid var(--accent-blue)',
            background: 'rgba(30, 58, 138, 0.15)',
          }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <div
                style={{
                  width: '10px',
                  height: '10px',
                  borderRadius: '50%',
                  background: demoRunning ? '#eab308' : '#10b981',
                  boxShadow: demoRunning ? '0 0 8px #eab308' : '0 0 8px #10b981',
                }}
              />
              <h3 style={{ fontSize: '15px', fontWeight: 600 }}>
                Section 29 Autonomous Demonstration: 14-Step End-to-End Reliability Lifecycle
              </h3>
            </div>
            <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
              {demoIncidentId && (
                <Link to={`/incidents/${demoIncidentId}`} className="btn btn-primary btn-sm">
                  Investigate Incident ({demoIncidentId.slice(0, 8)})
                  <ChevronRight size={14} />
                </Link>
              )}
              <button
                className="btn btn-secondary btn-sm"
                onClick={() => {
                  setDemoStepsList([]);
                  setDemoStatusMessage(null);
                }}
                disabled={demoRunning}
              >
                Dismiss
              </button>
            </div>
          </div>

          {demoStatusMessage && (
            <p style={{ fontSize: '13px', color: 'var(--text-secondary)', marginBottom: '16px' }}>
              {demoStatusMessage}
            </p>
          )}

          {/* 14 Steps Grid */}
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fill, minmax(240px, 1fr))',
              gap: '10px',
            }}
          >
            {[
              { num: 1, label: '1. Healthy Baseline' },
              { num: 2, label: '2. Inject RAG Degradation' },
              { num: 3, label: '3. ML Anomaly Detected' },
              { num: 4, label: '4. Incident Registered' },
              { num: 5, label: '5. Telemetry & Logs' },
              { num: 6, label: '6. Root Cause Diagnosed' },
              { num: 7, label: '7. RAG Runbook Retrieved' },
              { num: 8, label: '8. Recovery Simulated' },
              { num: 9, label: '9. Risk Calculated' },
              { num: 10, label: '10. Approval Requested' },
              { num: 11, label: '11. MCP Tool Executed' },
              { num: 12, label: '12. Telemetry Verified' },
              { num: 13, label: '13. Recovery Evaluated' },
              { num: 14, label: '14. Postmortem & Learned' },
            ].map((st) => {
              const stepData = demoStepsList.find((s) => s.step === st.num);
              const isCompleted = Boolean(stepData);
              const isCurrent = demoRunning && demoActiveStep === st.num;

              return (
                <div
                  key={st.num}
                  style={{
                    padding: '10px 12px',
                    borderRadius: 'var(--radius-sm)',
                    background: isCompleted
                      ? 'rgba(16, 185, 129, 0.1)'
                      : isCurrent
                      ? 'rgba(234, 179, 8, 0.15)'
                      : 'rgba(255, 255, 255, 0.03)',
                    border: `1px solid ${
                      isCompleted
                        ? 'rgba(16, 185, 129, 0.3)'
                        : isCurrent
                        ? 'rgba(234, 179, 8, 0.5)'
                        : 'var(--border-subtle)'
                    }`,
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '4px',
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span
                      style={{
                        fontSize: '12px',
                        fontWeight: 600,
                        color: isCompleted ? '#34d399' : isCurrent ? '#fbbf24' : 'var(--text-muted)',
                      }}
                    >
                      {st.label}
                    </span>
                    {isCompleted && <CheckCircle size={14} color="#34d399" />}
                    {isCurrent && <RefreshCw size={14} className="spin" color="#fbbf24" />}
                  </div>
                  {stepData?.description && (
                    <span style={{ fontSize: '11px', color: 'var(--text-secondary)', lineHeight: '1.3' }}>
                      {stepData.description.slice(0, 85)}...
                    </span>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}

      {error && (
        <div
          style={{
            background: 'var(--status-danger-bg)',
            border: '1px solid var(--status-danger-border)',
            padding: '12px 16px',
            borderRadius: 'var(--radius-sm)',
            marginBottom: '20px',
            color: '#f87171',
            display: 'flex',
            alignItems: 'center',
            gap: '10px',
          }}
        >
          <AlertCircle size={18} />
          <span>{error}</span>
        </div>
      )}

      {/* 10 Live Telemetry Metric Cards */}
      <div className="metrics-grid">
        <MetricCard
          label="Latency"
          value={cur.latency ?? 0}
          unit="s"
          threshold="<= 2.20s"
          isBreached={(cur.latency ?? 0) > 2.2}
          history={getMetricHistory('latency')}
          icon={<Clock size={14} />}
        />

        <MetricCard
          label="Error Rate"
          value={((cur.error_rate ?? 0) * 100).toFixed(1)}
          unit="%"
          threshold="<= 2.0%"
          isBreached={(cur.error_rate ?? 0) > 0.02}
          history={getMetricHistory('error_rate').map((v) => v * 100)}
          icon={<AlertCircle size={14} />}
        />

        <MetricCard
          label="RAG Retrieval Score"
          value={cur.retrieval_score ?? 0}
          threshold=">= 0.85"
          isBreached={(cur.retrieval_score ?? 1) < 0.85}
          history={getMetricHistory('retrieval_score')}
          icon={<Database size={14} />}
        />

        <MetricCard
          label="Answer Relevance"
          value={cur.answer_relevance ?? (1 - Number(cur.hallucination_score ?? 0))}
          threshold=">= 0.88"
          isBreached={Number(cur.answer_relevance ?? (1 - Number(cur.hallucination_score ?? 0))) < 0.88}
          history={getMetricHistory('answer_relevance')}
          icon={<Layers size={14} />}
        />

        <MetricCard
          label="Tool Failure Rate"
          value={((cur.tool_failure_rate ?? 0) * 100).toFixed(1)}
          unit="%"
          threshold="<= 3.0%"
          isBreached={(cur.tool_failure_rate ?? 0) > 0.03}
          history={getMetricHistory('tool_failure_rate').map((v) => v * 100)}
          icon={<Zap size={14} />}
        />

        <MetricCard
          label="Context Token Count"
          value={cur.token_count ?? cur.token_usage ?? 0}
          threshold="<= 1,500"
          isBreached={Number(cur.token_count ?? cur.token_usage ?? 0) > 1500}
          history={getMetricHistory('token_count')}
          icon={<Flame size={14} />}
        />

        <MetricCard
          label="Cost Per Query"
          value={`$${Number(cur.cost_per_query ?? (Number(cur.token_usage ?? cur.token_count ?? 500) * 0.00003)).toFixed(3)}`}
          threshold="<= $0.050"
          isBreached={Number(cur.cost_per_query ?? (Number(cur.token_usage ?? cur.token_count ?? 500) * 0.00003)) > 0.05}
          history={getMetricHistory('cost_per_query')}
          icon={<Coins size={14} />}
        />

        <MetricCard
          label="Agent Loop Count"
          value={Math.round(cur.loop_count ?? 0)}
          threshold="<= 1"
          isBreached={(cur.loop_count ?? 0) > 1}
          history={getMetricHistory('loop_count')}
          icon={<Repeat size={14} />}
          format="integer"
        />

        <MetricCard
          label="API Success Rate"
          value={((cur.api_success_rate ?? 1) * 100).toFixed(1)}
          unit="%"
          threshold=">= 98.0%"
          isBreached={(cur.api_success_rate ?? 1) < 0.98}
          history={getMetricHistory('api_success_rate').map((v) => v * 100)}
          icon={<ShieldAlert size={14} />}
        />

        <MetricCard
          label="CPU Utilization"
          value={(cur.cpu_utilization !== undefined ? (Number(cur.cpu_utilization) * (Number(cur.cpu_utilization) <= 1.0 ? 100 : 1)) : Number(cur.cpu_usage ?? 0)).toFixed(1)}
          unit="%"
          threshold="<= 80.0%"
          isBreached={Number(cur.cpu_utilization ?? (Number(cur.cpu_usage ?? 0) / 100)) > 0.8}
          history={getMetricHistory('cpu_utilization').map((v) => (v <= 1.0 ? v * 100 : v))}
          icon={<Cpu size={14} />}
        />
      </div>

      {/* Real-time Telemetry Trend & Active Incident Feed */}
      <div style={{ display: 'grid', gridTemplateColumns: '1.4fr 1fr', gap: '20px', marginBottom: '24px' }}>
        <div className="card">
          <div className="card-header">
            <h3 className="card-title">
              <Activity size={16} style={{ color: '#3b82f6' }} />
              Telemetry Trend Window (Last 40 Snapshots)
            </h3>
            <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Updated 2s ago</span>
          </div>
          {renderTrendChart()}
        </div>

        <div className="card">
          <div className="card-header">
            <h3 className="card-title">
              <ShieldAlert size={16} style={{ color: isAnyBreached ? '#ef4444' : '#10b981' }} />
              Active System Status
            </h3>
            <span className={`badge ${isAnyBreached ? 'badge-critical' : 'badge-low'}`}>
              {isAnyBreached ? 'DEGRADED' : 'HEALTHY'}
            </span>
          </div>
          <div style={{ fontSize: '13px', lineHeight: 1.6 }}>
            <p style={{ color: 'var(--text-secondary)', marginBottom: '12px' }}>
              {isAnyBreached
                ? 'Anomaly detected! Metrics have breached operational thresholds. ARGUS Multi-Agent graph is actively correlating telemetry against semantic runbooks.'
                : 'All production metrics within normal operational bounds. Anomaly detector (Z-Score + Isolation Forest) is monitoring stream at 2s frequency.'}
            </p>
            <div
              style={{
                background: 'var(--bg-canvas)',
                padding: '12px',
                borderRadius: 'var(--radius-sm)',
                border: '1px solid var(--border-subtle)',
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '6px' }}>
                <span style={{ color: 'var(--text-muted)' }}>Baseline Latency</span>
                <span className="mono">0.85s - 1.20s</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '6px' }}>
                <span style={{ color: 'var(--text-muted)' }}>Baseline Error Rate</span>
                <span className="mono">&lt; 0.5%</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: 'var(--text-muted)' }}>Detector Ensemble</span>
                <span className="mono" style={{ color: '#10b981' }}>Z-Score (2.8σ) + Isolation Forest</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Recent Incidents Feed */}
      <div className="card">
        <div className="card-header">
          <h3 className="card-title">
            <AlertCircle size={16} style={{ color: '#f59e0b' }} />
            Recent Incidents
          </h3>
          <Link to="/incidents" className="btn btn-secondary btn-sm">
            View All ({recentIncidents.length})
            <ExternalLink size={12} />
          </Link>
        </div>

        <div className="table-container">
          <table className="data-table">
            <thead>
              <tr>
                <th>ID</th>
                <th>Title</th>
                <th>Failure Type</th>
                <th>Severity</th>
                <th>Confidence</th>
                <th>Status</th>
                <th>Created</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {recentIncidents.length === 0 ? (
                <tr>
                  <td colSpan={8} style={{ textAlign: 'center', color: 'var(--text-muted)', padding: '24px' }}>
                    No recorded incidents. System running cleanly.
                  </td>
                </tr>
              ) : (
                recentIncidents.slice(0, 6).map((inc) => (
                  <tr key={inc.id}>
                    <td className="mono" style={{ fontSize: '12px', color: '#3b82f6' }}>
                      <Link to={`/incidents/${inc.id}`}>{inc.id.slice(0, 8)}</Link>
                    </td>
                    <td style={{ fontWeight: 500, color: 'var(--text-primary)' }}>{inc.title}</td>
                    <td>
                      <span className="badge badge-purple">{inc.failure_type}</span>
                    </td>
                    <td>
                      <StatusBadge type="severity" value={inc.severity} />
                    </td>
                    <td className="mono">{(((inc.confidence ?? 0.9)) * 100).toFixed(0)}%</td>
                    <td>
                      <StatusBadge type="status" value={inc.status} />
                    </td>
                    <td className="mono" style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                      {new Date(inc.created_at).toLocaleTimeString()}
                    </td>
                    <td>
                      <Link to={`/incidents/${inc.id}`} className="btn btn-secondary btn-sm" style={{ padding: '2px 8px' }}>
                        Investigate
                      </Link>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
