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
  Repeat,
  ShieldAlert,
  Zap,
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

  const loadData = async () => {
    try {
      const [mRes, iRes] = await Promise.all([
        api.getMetrics(40),
        api.getIncidents(10),
      ]);
      setCurrentMetrics(mRes.current);
      setHistory(mRes.history || []);
      setRecentIncidents(iRes || []);
      setError(null);
    } catch (err: any) {
      setError(err.message || 'Failed to fetch dashboard metrics');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 2000);
    return () => clearInterval(interval);
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
    return history.map((h) => Number(h[key]) || 0);
  };

  // Render SVG multi-series trend line chart
  const renderTrendChart = () => {
    if (history.length < 2) return null;
    const width = 800;
    const height = 180;
    const latVals = history.map((h) => h.latency);
    const maxLat = Math.max(...latVals, 4.0);

    const latPoints = history
      .map((h, i) => {
        const x = (i / (history.length - 1)) * width;
        const y = height - (h.latency / maxLat) * (height - 30) - 15;
        return `${x.toFixed(1)},${y.toFixed(1)}`;
      })
      .join(' ');

    const errPoints = history
      .map((h, i) => {
        const x = (i / (history.length - 1)) * width;
        const y = height - (h.error_rate / 0.25) * (height - 30) - 15;
        return `${x.toFixed(1)},${y.toFixed(1)}`;
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
          <Link to="/simulation" className="btn btn-primary btn-sm">
            <Flame size={14} />
            Inject Test Fault
          </Link>
          <Link to="/evaluation" className="btn btn-secondary btn-sm">
            <Activity size={14} />
            View Benchmark
          </Link>
        </div>
      </div>

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
          value={cur.latency}
          unit="s"
          threshold="<= 2.20s"
          isBreached={cur.latency > 2.2}
          history={getMetricHistory('latency')}
          icon={<Clock size={14} />}
        />

        <MetricCard
          label="Error Rate"
          value={(cur.error_rate * 100).toFixed(1)}
          unit="%"
          threshold="<= 2.0%"
          isBreached={cur.error_rate > 0.02}
          history={getMetricHistory('error_rate').map((v) => v * 100)}
          icon={<AlertCircle size={14} />}
        />

        <MetricCard
          label="RAG Retrieval Score"
          value={cur.retrieval_score}
          threshold=">= 0.85"
          isBreached={cur.retrieval_score < 0.85}
          history={getMetricHistory('retrieval_score')}
          icon={<Database size={14} />}
        />

        <MetricCard
          label="Answer Relevance"
          value={cur.answer_relevance}
          threshold=">= 0.88"
          isBreached={cur.answer_relevance < 0.88}
          history={getMetricHistory('answer_relevance')}
          icon={<Layers size={14} />}
        />

        <MetricCard
          label="Tool Failure Rate"
          value={(cur.tool_failure_rate * 100).toFixed(1)}
          unit="%"
          threshold="<= 3.0%"
          isBreached={cur.tool_failure_rate > 0.03}
          history={getMetricHistory('tool_failure_rate').map((v) => v * 100)}
          icon={<Zap size={14} />}
        />

        <MetricCard
          label="Context Token Count"
          value={cur.token_count}
          threshold="<= 1,500"
          isBreached={cur.token_count > 1500}
          history={getMetricHistory('token_count')}
          icon={<Flame size={14} />}
        />

        <MetricCard
          label="Cost Per Query"
          value={`$${cur.cost_per_query.toFixed(3)}`}
          threshold="<= $0.050"
          isBreached={cur.cost_per_query > 0.05}
          history={getMetricHistory('cost_per_query')}
          icon={<Coins size={14} />}
        />

        <MetricCard
          label="Agent Loop Count"
          value={cur.loop_count}
          threshold="<= 1"
          isBreached={cur.loop_count > 1}
          history={getMetricHistory('loop_count')}
          icon={<Repeat size={14} />}
        />

        <MetricCard
          label="API Success Rate"
          value={(cur.api_success_rate * 100).toFixed(1)}
          unit="%"
          threshold=">= 98.0%"
          isBreached={cur.api_success_rate < 0.98}
          history={getMetricHistory('api_success_rate').map((v) => v * 100)}
          icon={<ShieldAlert size={14} />}
        />

        <MetricCard
          label="CPU Utilization"
          value={(cur.cpu_utilization * 100).toFixed(1)}
          unit="%"
          threshold="<= 80.0%"
          isBreached={cur.cpu_utilization > 0.8}
          history={getMetricHistory('cpu_utilization').map((v) => v * 100)}
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
                    <td className="mono">{((inc.confidence || 0.9) * 100).toFixed(0)}%</td>
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
