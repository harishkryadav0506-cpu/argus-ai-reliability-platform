import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import {
  AlertTriangle,
  CheckCircle,
  Filter,
  Flame,
  Search,
  ShieldAlert,
  ArrowUpDown,
  RefreshCw,
} from 'lucide-react';
import { api } from '../services/api';
import { Incident } from '../types';
import { StatusBadge } from '../components/StatusBadge';

export const IncidentsPage: React.FC = () => {
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [severityFilter, setSeverityFilter] = useState<string>('ALL');
  const [statusFilter, setStatusFilter] = useState<string>('ALL');
  const [failureTypeFilter, setFailureTypeFilter] = useState<string>('ALL');
  const [isRefreshing, setIsRefreshing] = useState<boolean>(false);
  const [globalCounts, setGlobalCounts] = useState<{
    total: number;
    unresolved: number;
    active: number;
    open: number;
    investigating: number;
    mitigating?: number;
    escalated: number;
    resolved: number;
  } | null>(null);

  const isMountedRef = React.useRef(true);

  const fetchIncidents = async () => {
    setIsRefreshing(true);
    try {
      const [data, countData] = await Promise.all([
        api.getIncidents(100),
        api.getIncidentCount().catch(() => null),
      ]);
      if (!isMountedRef.current) return;
      setIncidents(data || []);
      if (countData) {
        setGlobalCounts(countData);
      }
    } catch (e) {
      if (isMountedRef.current) {
        console.error('Failed to load incidents:', e);
      }
    } finally {
      if (isMountedRef.current) {
        setLoading(false);
        setIsRefreshing(false);
      }
    }
  };

  useEffect(() => {
    isMountedRef.current = true;
    fetchIncidents();
    return () => {
      isMountedRef.current = false;
    };
  }, []);

  const filteredIncidents = incidents.filter((inc) => {
    const matchesSearch =
      inc.id.toLowerCase().includes(searchQuery.toLowerCase()) ||
      inc.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      inc.failure_type.toLowerCase().includes(searchQuery.toLowerCase());

    const matchesSeverity =
      severityFilter === 'ALL' || inc.severity.toUpperCase() === severityFilter;

    const matchesStatus =
      statusFilter === 'ALL' || inc.status.toUpperCase() === statusFilter;

    const matchesFailureType =
      failureTypeFilter === 'ALL' || inc.failure_type === failureTypeFilter;

    return matchesSearch && matchesSeverity && matchesStatus && matchesFailureType;
  });

  const totalCount = globalCounts ? globalCounts.total : incidents.length;
  const activeCount = globalCounts
    ? (globalCounts.active ?? (globalCounts.open + globalCounts.investigating + (globalCounts.mitigating || 0)))
    : incidents.filter((i) => i.status === 'open' || i.status === 'investigating').length;
  const resolvedCount = globalCounts
    ? globalCounts.resolved
    : incidents.filter((i) => i.status === 'resolved').length;
  const escalatedCount = globalCounts
    ? globalCounts.escalated
    : incidents.filter((i) => i.status === 'escalated').length;

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">Incidents & Root Cause Investigations</h1>
          <p className="page-desc">
            Historical and active operational incidents detected by the ML anomaly ensemble and resolved via LangGraph agents.
          </p>
        </div>
        <div style={{ display: 'flex', gap: '8px' }}>
          <button
            className="btn btn-secondary btn-sm"
            onClick={fetchIncidents}
            disabled={isRefreshing}
          >
            <RefreshCw size={13} className={isRefreshing ? 'spin' : ''} />
            Refresh
          </button>
          <Link to="/simulation" className="btn btn-primary btn-sm">
            <Flame size={13} />
            Simulate Incident
          </Link>
        </div>
      </div>

      {/* Summary Chips */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '16px', marginBottom: '20px' }}>
        <div className="card" style={{ padding: '14px 18px' }}>
          <div style={{ fontSize: '11px', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Total Incidents</div>
          <div className="mono" style={{ fontSize: '22px', fontWeight: 700, marginTop: '4px' }}>{totalCount}</div>
        </div>

        <div className="card" style={{ padding: '14px 18px', borderColor: activeCount > 0 ? 'var(--status-warn-border)' : 'var(--border-subtle)' }}>
          <div style={{ fontSize: '11px', color: 'var(--status-warn)', textTransform: 'uppercase' }}>Active / Investigating</div>
          <div className="mono" style={{ fontSize: '22px', fontWeight: 700, marginTop: '4px', color: '#fbbf24' }}>{activeCount}</div>
        </div>

        <div className="card" style={{ padding: '14px 18px' }}>
          <div style={{ fontSize: '11px', color: 'var(--status-pass)', textTransform: 'uppercase' }}>Resolved & Verified</div>
          <div className="mono" style={{ fontSize: '22px', fontWeight: 700, marginTop: '4px', color: '#34d399' }}>{resolvedCount}</div>
        </div>

        <div className="card" style={{ padding: '14px 18px', borderColor: escalatedCount > 0 ? 'var(--status-danger-border)' : 'var(--border-subtle)' }}>
          <div style={{ fontSize: '11px', color: 'var(--status-danger)', textTransform: 'uppercase' }}>Escalated to Human</div>
          <div className="mono" style={{ fontSize: '22px', fontWeight: 700, marginTop: '4px', color: '#f87171' }}>{escalatedCount}</div>
        </div>
      </div>

      {/* Search & Filters Bar */}
      <div
        className="card"
        style={{
          padding: '14px 18px',
          marginBottom: '20px',
          display: 'flex',
          flexWrap: 'wrap',
          alignItems: 'center',
          gap: '14px',
          justifyContent: 'space-between',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flex: '1', minWidth: '240px' }}>
          <Search size={16} style={{ color: 'var(--text-muted)' }} />
          <input
            type="text"
            className="input-text"
            placeholder="Search by ID, title, or failure type..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            style={{ width: '100%', maxWidth: '340px' }}
          />
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flexWrap: 'wrap' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '12px', color: 'var(--text-muted)' }}>
            <Filter size={13} />
            Filters:
          </div>

          <select
            className="input-select"
            value={severityFilter}
            onChange={(e) => setSeverityFilter(e.target.value)}
          >
            <option value="ALL">Severity: All</option>
            <option value="CRITICAL">Critical</option>
            <option value="HIGH">High</option>
            <option value="MEDIUM">Medium</option>
            <option value="LOW">Low</option>
          </select>

          <select
            className="input-select"
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
          >
            <option value="ALL">Status: All</option>
            <option value="INVESTIGATING">Investigating</option>
            <option value="RESOLVED">Resolved</option>
            <option value="ESCALATED">Escalated</option>
            <option value="OPEN">Open</option>
          </select>

          <select
            className="input-select"
            value={failureTypeFilter}
            onChange={(e) => setFailureTypeFilter(e.target.value)}
          >
            <option value="ALL">Failure Type: All</option>
            <option value="LATENCY_SPIKE">LATENCY_SPIKE</option>
            <option value="LLM_FAILURE">LLM_FAILURE</option>
            <option value="RAG_DEGRADATION">RAG_DEGRADATION</option>
            <option value="RETRIEVAL_FAILURE">RETRIEVAL_FAILURE</option>
            <option value="TOOL_FAILURE">TOOL_FAILURE</option>
            <option value="API_FAILURE">API_FAILURE</option>
            <option value="COST_SPIKE">COST_SPIKE</option>
            <option value="AGENT_LOOP">AGENT_LOOP</option>
            <option value="DATA_QUALITY">DATA_QUALITY</option>
            <option value="UNKNOWN">UNKNOWN</option>
          </select>
        </div>
      </div>

      {/* Incidents Table */}
      <div className="table-container">
        <table className="data-table">
          <thead>
            <tr>
              <th>Incident ID</th>
              <th>Incident Title</th>
              <th>Failure Classification</th>
              <th>Severity</th>
              <th>Confidence</th>
              <th>Status</th>
              <th>Detected At</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td colSpan={8} style={{ textAlign: 'center', padding: '32px', color: 'var(--text-muted)' }}>
                  Loading recorded incidents...
                </td>
              </tr>
            ) : filteredIncidents.length === 0 ? (
              <tr>
                <td colSpan={8} style={{ textAlign: 'center', padding: '32px', color: 'var(--text-muted)' }}>
                  No incidents match the active search and filter criteria.
                </td>
              </tr>
            ) : (
              filteredIncidents.map((inc) => (
                <tr key={inc.id}>
                  <td className="mono" style={{ fontSize: '12px', fontWeight: 600 }}>
                    <Link to={`/incidents/${inc.id}`} style={{ color: '#3b82f6' }}>
                      {inc.id.slice(0, 8)}
                    </Link>
                  </td>
                  <td>
                    <div style={{ fontWeight: 600, color: 'var(--text-primary)', marginBottom: '2px' }}>
                      <Link to={`/incidents/${inc.id}`}>{inc.title}</Link>
                    </div>
                    <div style={{ fontSize: '12px', color: 'var(--text-muted)', maxWidth: '450px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {inc.description}
                    </div>
                  </td>
                  <td>
                    <span className="badge badge-purple">{inc.failure_type}</span>
                  </td>
                  <td>
                    <StatusBadge type="severity" value={inc.severity} />
                  </td>
                  <td className="mono" style={{ fontWeight: 600 }}>
                    {(((inc.confidence ?? 0.9)) * 100).toFixed(0)}%
                  </td>
                  <td>
                    <StatusBadge type="status" value={inc.status} />
                  </td>
                  <td className="mono" style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                    {new Date(inc.created_at).toLocaleString()}
                  </td>
                  <td>
                    <Link
                      to={`/incidents/${inc.id}`}
                      className="btn btn-secondary btn-sm"
                      style={{ padding: '3px 10px' }}
                    >
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
  );
};
