import React from 'react';

interface StatusBadgeProps {
  type: 'severity' | 'status' | 'risk' | 'approval';
  value: string;
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({ type, value }) => {
  const val = (value || '').toLowerCase();

  let className = 'badge';

  if (type === 'severity') {
    if (val === 'critical') className += ' badge-critical';
    else if (val === 'high') className += ' badge-high';
    else if (val === 'medium') className += ' badge-medium';
    else className += ' badge-low';
  } else if (type === 'status') {
    if (val === 'resolved') className += ' badge-low';
    else if (val === 'investigating' || val === 'open') className += ' badge-high';
    else if (val === 'escalated') className += ' badge-critical';
    else className += ' badge-info';
  } else if (type === 'risk') {
    if (val === 'high') className += ' badge-critical';
    else if (val === 'medium') className += ' badge-medium';
    else className += ' badge-low';
  } else if (type === 'approval') {
    if (val === 'approved') className += ' badge-low';
    else if (val === 'rejected') className += ' badge-critical';
    else className += ' badge-medium';
  }

  return <span className={className}>{value.toUpperCase()}</span>;
};
