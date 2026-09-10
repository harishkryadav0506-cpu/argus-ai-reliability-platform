import React, { useState, useEffect } from 'react';
import { NavLink, useLocation } from 'react-router-dom';
import {
  Activity,
  AlertTriangle,
  GitBranch,
  BarChart3,
  Cpu,
  Settings as SettingsIcon,
  ShieldCheck,
  RefreshCw,
} from 'lucide-react';
import { api } from '../services/api';

export const Navbar: React.FC = () => {
  const [activeFault, setActiveFault] = useState<string | null>(null);
  const [incidentCount, setIncidentCount] = useState<number>(0);
  const [isResetting, setIsResetting] = useState<boolean>(false);
  const location = useLocation();

  const fetchStatus = async () => {
    try {
      const metricsData = await api.getMetrics(5);
      const cur = metricsData.current;
      // If error_rate > 0.05 or latency > 2.5 or tool_failure_rate > 0.05, consider degraded
      if (cur.error_rate > 0.05) setActiveFault('HIGH ERROR RATE');
      else if (cur.latency > 2.2) setActiveFault('LATENCY SPIKE');
      else if (cur.tool_failure_rate > 0.05) setActiveFault('TOOL CASCADE');
      else if (cur.cost_per_query > 0.08) setActiveFault('COST SPIKE');
      else setActiveFault(null);

      const incs = await api.getIncidents(50);
      const unresolved = incs.filter(
        (i) => i.status === 'open' || i.status === 'investigating' || i.status === 'escalated'
      ).length;
      setIncidentCount(unresolved);
    } catch {
      // ignore in background polling
    }
  };

  useEffect(() => {
    fetchStatus();
    const timer = setInterval(fetchStatus, 3000);
    return () => clearInterval(timer);
  }, [location.pathname]);

  const handleReset = async () => {
    setIsResetting(true);
    try {
      await api.resetSimulation();
      await fetchStatus();
    } catch (e) {
      console.error('Failed to reset simulation:', e);
    } finally {
      setIsResetting(false);
    }
  };

  return (
    <header className="navbar">
      <div className="nav-inner">
        <div className="brand-section">
          <div className="brand-logo">A</div>
          <div>
            <div className="brand-title">ARGUS</div>
            <div className="brand-subtitle">Autonomous Reliability & Recovery</div>
          </div>
        </div>

        <nav className="nav-links">
          <NavLink to="/" className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}>
            <Activity size={15} />
            Dashboard
          </NavLink>

          <NavLink to="/incidents" className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}>
            <AlertTriangle size={15} />
            Incidents
            {incidentCount > 0 && (
              <span className="badge badge-critical" style={{ padding: '1px 6px', fontSize: '10px' }}>
                {incidentCount}
              </span>
            )}
          </NavLink>

          <NavLink to="/trace" className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}>
            <GitBranch size={15} />
            Agent Trace
          </NavLink>

          <NavLink to="/evaluation" className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}>
            <BarChart3 size={15} />
            Evaluation
          </NavLink>

          <NavLink to="/simulation" className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}>
            <Cpu size={15} />
            Simulation
          </NavLink>

          <NavLink to="/settings" className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}>
            <SettingsIcon size={15} />
            Settings
          </NavLink>
        </nav>

        <div className="nav-status">
          {activeFault ? (
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <div className="status-pill degraded">
                <span className="pulse-dot"></span>
                FAULT: {activeFault}
              </div>
              <button
                className="btn btn-secondary btn-sm"
                onClick={handleReset}
                disabled={isResetting}
                title="Reset simulation to healthy baseline"
              >
                <RefreshCw size={12} className={isResetting ? 'spin' : ''} />
                Reset
              </button>
            </div>
          ) : (
            <div className="status-pill healthy">
              <span className="pulse-dot"></span>
              <ShieldCheck size={13} style={{ marginRight: '2px' }} />
              LIVE MONITORING
            </div>
          )}
        </div>
      </div>
    </header>
  );
};
