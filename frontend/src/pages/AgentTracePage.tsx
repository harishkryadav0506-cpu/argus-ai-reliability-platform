import React, { useState, useEffect } from 'react';
import { useSearchParams, Link } from 'react-router-dom';
import {
  Activity,
  AlertTriangle,
  ArrowRight,
  CheckCircle,
  Clock,
  Cpu,
  Database,
  ExternalLink,
  FileText,
  GitBranch,
  Play,
  RotateCcw,
  Shield,
  ShieldAlert,
  Terminal,
  UserCheck,
  Zap,
} from 'lucide-react';
import { api } from '../services/api';
import { Incident } from '../types';
import { StatusBadge } from '../components/StatusBadge';

interface TraceNode {
  id: string;
  name: string;
  agent: string;
  status: 'completed' | 'active' | 'waiting' | 'skipped';
  duration: string;
  description: string;
  details: Record<string, any>;
}

export const AgentTracePage: React.FC = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const incidentIdParam = searchParams.get('incident_id') || '';

  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [selectedIncidentId, setSelectedIncidentId] = useState<string>(incidentIdParam);
  const [selectedIncident, setSelectedIncident] = useState<Incident | null>(null);
  const [activeNodeId, setActiveNodeId] = useState<string>('detection');
  const [loading, setLoading] = useState<boolean>(true);

  useEffect(() => {
    const fetchIncidentsList = async () => {
      try {
        const list = await api.getIncidents(50);
        setIncidents(list || []);
        if (!selectedIncidentId && list.length > 0) {
          setSelectedIncidentId(list[0].id);
        }
      } catch (e) {
        console.error('Failed to load incidents list for trace:', e);
      } finally {
        setLoading(false);
      }
    };
    fetchIncidentsList();
  }, []);

  useEffect(() => {
    if (selectedIncidentId) {
      api.getIncident(selectedIncidentId).then((data) => {
        setSelectedIncident(data);
      }).catch((e) => console.error(e));
    }
  }, [selectedIncidentId]);

  const handleSelectIncident = (id: string) => {
    setSelectedIncidentId(id);
    setSearchParams({ incident_id: id });
  };

  const failureType = selectedIncident?.failure_type || 'LATENCY_SPIKE';
  const isResolved = selectedIncident?.status === 'resolved';

  const traceNodes: TraceNode[] = [
    {
      id: 'detection',
      name: 'Anomaly Detection',
      agent: 'DetectionAgent',
      status: 'completed',
      duration: '42ms',
      description: 'Z-score rolling mean threshold (2.8σ) + Isolation Forest anomaly ensemble',
      details: {
        detector: 'Ensemble (Rolling Z-score + Isolation Forest)',
        anomaly_detected: true,
        detected_severity: selectedIncident?.severity || 'high',
        confidence: selectedIncident?.confidence || 0.94,
        metrics_evaluated: ['latency', 'error_rate', 'retrieval_score', 'tool_failure_rate'],
      },
    },
    {
      id: 'retrieval',
      name: 'Runbook Retrieval',
      agent: 'RAGRetrieval',
      status: 'completed',
      duration: '115ms',
      description: 'Semantic vector search against ChromaDB operational runbooks',
      details: {
        vector_db: 'ChromaDB local ONNX store',
        embedding_model: 'all-MiniLM-L6-v2 (384-dim dense vectors)',
        top_k: 3,
        retrieved_sources: [
          `RB-001_${failureType}.md`,
          'RB-006_LATENCY_SPIKE.md',
          'RB-004_TOOL_FAILURE.md',
        ],
        relevance_score: 0.88,
      },
    },
    {
      id: 'diagnosis',
      name: 'Root Cause Diagnosis',
      agent: 'DiagnosisAgent',
      status: 'completed',
      duration: '840ms',
      description: 'Google Gemini structured output requiring runbook evidence citations',
      details: {
        llm_model: 'gemini-3.6-flash (via ChatGoogleGenerativeAI)',
        diagnosed_fault: failureType,
        evidence_citations: [
          `Telemetry deviation matched ${failureType} SLA breach signature`,
          'Cited section: Section 3 Runbook Symptom Mapping',
        ],
        confidence: 0.92,
      },
    },
    {
      id: 'recovery',
      name: 'Strategy Simulation',
      agent: 'RecoveryAgent',
      status: 'completed',
      duration: '180ms',
      description: 'Counterfactual simulator evaluating recovery probabilities and risk bounds',
      details: {
        evaluated_strategies: [
          { strategy: 'restart_service', probability: 0.92, risk: 'low' },
          { strategy: 'execute_rollback', probability: 0.85, risk: 'high' },
        ],
        selected_strategy: 'restart_service',
        approval_required: true,
      },
    },
    {
      id: 'approval',
      name: 'Human Approval Gate',
      agent: 'LangGraph Interrupt',
      status: isResolved ? 'completed' : 'active',
      duration: isResolved ? '1.2s' : 'Waiting',
      description: 'Native LangGraph interrupt/resume pattern halting execution until human consent',
      details: {
        pattern: 'LangGraph interrupt() & Command(resume={approved: True/False})',
        status: isResolved ? 'Approved by operator:engineer' : 'Awaiting operator consent',
        allowlist_checked: true,
      },
    },
    {
      id: 'execution',
      name: 'MCP Action Execution',
      agent: 'MCPServer (restart_service)',
      status: isResolved ? 'completed' : 'waiting',
      duration: isResolved ? '310ms' : '—',
      description: 'Allowlist-enforced action execution with pre/post AuditLog recording',
      details: {
        mcp_tool: 'restart_service',
        tool_risk: 'high',
        audit_log_written: isResolved,
        result: isResolved ? 'SUCCESS: Service restarted cleanly' : 'Pending execution',
      },
    },
    {
      id: 'verification',
      name: 'SLA Telemetry Verification',
      agent: 'VerificationNode',
      status: isResolved ? 'completed' : 'waiting',
      duration: isResolved ? '250ms' : '—',
      description: 'Compares post-recovery telemetry against operational baseline SLA bounds',
      details: {
        verification_result: isResolved ? 'recovery_verified: true' : 'Pending',
        retry_bound: 'Max 3 retries (bounded retry loop)',
        telemetry_status: isResolved ? 'Returned within SLA limits' : 'Unverified',
      },
    },
    {
      id: 'postmortem',
      name: 'Postmortem & Learning',
      agent: 'PostmortemAgent',
      status: isResolved ? 'completed' : 'waiting',
      duration: isResolved ? '450ms' : '—',
      description: 'Generates postmortem Markdown and auto-ingests incident into ChromaDB (Section 37.4)',
      details: {
        postmortem_generated: isResolved,
        experience_learning_ingested: isResolved,
        vector_collection: 'historical_incidents',
      },
    },
  ];

  const activeNode = traceNodes.find((n) => n.id === activeNodeId) || traceNodes[0];

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">Agent Execution Trace & Graph Inspector</h1>
          <p className="page-desc">
            Visual inspection of the Section 3 LangGraph state machine, node transitions, and evidence grounding.
          </p>
        </div>

        {/* Incident Selector */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <label style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Inspect Incident:</label>
          <select
            className="input-select"
            value={selectedIncidentId}
            onChange={(e) => handleSelectIncident(e.target.value)}
            style={{ maxWidth: '320px' }}
          >
            {incidents.map((inc) => (
              <option key={inc.id} value={inc.id}>
                [{inc.severity.toUpperCase()}] {inc.title.slice(0, 32)}... ({inc.id.slice(0, 6)})
              </option>
            ))}
          </select>
        </div>
      </div>

      {selectedIncident && (
        <div
          className="card"
          style={{
            marginBottom: '20px',
            padding: '12px 18px',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            flexWrap: 'wrap',
            gap: '12px',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <span className="mono" style={{ color: '#3b82f6', fontWeight: 600 }}>
              {selectedIncident.id}
            </span>
            <StatusBadge type="severity" value={selectedIncident.severity} />
            <StatusBadge type="status" value={selectedIncident.status} />
            <span className="badge badge-purple">{selectedIncident.failure_type}</span>
          </div>
          <Link
            to={`/incidents/${selectedIncident.id}`}
            style={{ display: 'flex', alignItems: 'center', gap: '4px', fontSize: '12px' }}
          >
            View Full Incident <ExternalLink size={12} />
          </Link>
        </div>
      )}

      {/* Main Multi-Agent Pipeline Visualization Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: '1.3fr 1fr', gap: '20px' }}>
        {/* Pipeline Nodes List */}
        <div className="card">
          <div className="card-header">
            <h3 className="card-title">
              <GitBranch size={16} style={{ color: '#8b5cf6' }} />
              LangGraph State Transitions (Section 3 & 10)
            </h3>
            <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Click node to inspect state</span>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
            {traceNodes.map((node, index) => {
              const isSelected = node.id === activeNodeId;
              return (
                <div
                  key={node.id}
                  onClick={() => setActiveNodeId(node.id)}
                  style={{
                    background: isSelected ? 'var(--bg-surface-elevated)' : 'var(--bg-canvas)',
                    border: `1px solid ${isSelected ? '#3b82f6' : 'var(--border-subtle)'}`,
                    borderRadius: 'var(--radius-sm)',
                    padding: '12px 16px',
                    cursor: 'pointer',
                    transition: 'all 0.15s ease',
                    boxShadow: isSelected ? '0 0 12px rgba(59, 130, 246, 0.2)' : 'none',
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <span
                        className="mono"
                        style={{
                          fontSize: '11px',
                          color: '#3b82f6',
                          background: 'rgba(59, 130, 246, 0.12)',
                          padding: '1px 6px',
                          borderRadius: '3px',
                        }}
                      >
                        0{index + 1}
                      </span>
                      <span style={{ fontWeight: 600, fontSize: '13px', color: isSelected ? '#fff' : 'var(--text-primary)' }}>
                        {node.name}
                      </span>
                      <span className="mono" style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                        ({node.agent})
                      </span>
                    </div>

                    <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                      <span className="mono" style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                        {node.duration}
                      </span>
                      <span
                        className={`badge ${
                          node.status === 'completed'
                            ? 'badge-low'
                            : node.status === 'active'
                            ? 'badge-high'
                            : 'badge-info'
                        }`}
                      >
                        {node.status.toUpperCase()}
                      </span>
                    </div>
                  </div>

                  <div style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
                    {node.description}
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Selected Node State Inspector */}
        <div className="card">
          <div className="card-header">
            <h3 className="card-title">
              <Terminal size={16} style={{ color: '#10b981' }} />
              Node State Inspector: {activeNode.name}
            </h3>
            <span className="badge badge-purple">{activeNode.agent}</span>
          </div>

          <div style={{ marginBottom: '16px' }}>
            <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginBottom: '4px' }}>
              Summary & Responsibility:
            </div>
            <p style={{ fontSize: '13px', color: 'var(--text-primary)', lineHeight: 1.5 }}>
              {activeNode.description}
            </p>
          </div>

          <div>
            <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginBottom: '6px' }}>
              Structured Graph Output & Evidence Metadata:
            </div>
            <pre
              className="mono"
              style={{
                background: 'var(--bg-canvas)',
                border: '1px solid var(--border-subtle)',
                borderRadius: 'var(--radius-sm)',
                padding: '14px',
                fontSize: '12px',
                color: '#38bdf8',
                maxHeight: '440px',
                overflowY: 'auto',
                lineHeight: 1.6,
              }}
            >
              {JSON.stringify(activeNode.details, null, 2)}
            </pre>
          </div>
        </div>
      </div>
    </div>
  );
};
