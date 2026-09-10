import React from 'react';

interface MetricCardProps {
  label: string;
  value: number | string;
  unit?: string;
  threshold?: string;
  isBreached?: boolean;
  history?: number[];
  icon?: React.ReactNode;
}

export const MetricCard: React.FC<MetricCardProps> = ({
  label,
  value,
  unit,
  threshold,
  isBreached,
  history = [],
  icon,
}) => {
  // Generate SVG points for mini sparkline
  const renderSparkline = () => {
    if (!history || history.length < 2) return null;
    const min = Math.min(...history);
    const max = Math.max(...history);
    const range = max - min || 1;
    const width = 120;
    const height = 28;

    const points = history
      .map((val, idx) => {
        const valNum = Number(val) || 0;
        const x = (idx / (history.length - 1)) * width;
        const y = height - ((valNum - min) / range) * (height - 6) - 3;
        return `${(x || 0).toFixed(1)},${(isNaN(y) ? 0 : y).toFixed(1)}`;
      })
      .join(' ');

    const strokeColor = isBreached ? '#ef4444' : '#3b82f6';
    const fillColor = isBreached ? 'rgba(239, 68, 68, 0.15)' : 'rgba(59, 130, 246, 0.1)';

    return (
      <svg width={width} height={height} style={{ overflow: 'visible' }}>
        <polyline
          fill="none"
          stroke={strokeColor}
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
          points={points}
        />
      </svg>
    );
  };

  return (
    <div className={`metric-card ${isBreached ? 'breached' : ''}`}>
      <div className="metric-label">
        <span style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          {icon}
          {label}
        </span>
        {isBreached && <span className="badge badge-critical">BREACH</span>}
      </div>

      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end' }}>
        <div className="metric-value-container">
          <span className="metric-value">
            {typeof value === 'number'
              ? isNaN(value)
                ? '0.0'
                : value.toFixed(value < 10 ? 3 : 1)
              : (value ?? '—')}
          </span>
          {unit && <span className="metric-unit">{unit}</span>}
        </div>
        <div>{renderSparkline()}</div>
      </div>

      {threshold && (
        <div className="metric-threshold">
          SLA Limit: <span style={{ color: isBreached ? '#f87171' : '#94a3b8' }}>{threshold}</span>
        </div>
      )}
    </div>
  );
};
