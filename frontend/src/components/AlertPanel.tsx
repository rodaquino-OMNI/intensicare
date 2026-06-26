import { useState } from 'react';
import { apiClient } from '../api/client';
import type { AlertInfo } from '../types';

interface AlertPanelProps {
  alerts: AlertInfo[];
  onAcknowledged: () => void;
}

const severityStyles: Record<string, string> = {
  critical: 'border-red-400 bg-red-50',
  warning: 'border-yellow-400 bg-yellow-50',
  info: 'border-blue-300 bg-blue-50',
};

const severityBadge: Record<string, string> = {
  critical: 'bg-red-500',
  warning: 'bg-yellow-500',
  info: 'bg-blue-500',
};

export default function AlertPanel({ alerts, onAcknowledged }: AlertPanelProps) {
  const [acknowledging, setAcknowledging] = useState<number | null>(null);

  const handleAcknowledge = async (alertId: number) => {
    setAcknowledging(alertId);
    try {
      await apiClient.acknowledgeAlert(alertId);
      onAcknowledged();
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to acknowledge alert');
    } finally {
      setAcknowledging(null);
    }
  };

  const formatDate = (iso: string) => {
    const d = new Date(iso);
    return d.toLocaleString();
  };

  const activeAlerts = alerts.filter((a) => a.status === 'active');

  return (
    <div>
      <h3 className="font-semibold text-slate-800 mb-3">
        Active Alerts ({activeAlerts.length})
      </h3>

      {activeAlerts.length === 0 ? (
        <div className="text-sm text-slate-400 text-center py-6">
          No active alerts
        </div>
      ) : (
        <div className="space-y-2 max-h-96 overflow-y-auto">
          {activeAlerts.map((alert) => (
            <div
              key={alert.id}
              className={`border rounded-lg p-3 ${severityStyles[alert.severity] || 'border-gray-200'}`}
            >
              <div className="flex items-start justify-between gap-2">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <span
                      className={`inline-block w-2 h-2 rounded-full ${severityBadge[alert.severity] || 'bg-gray-400'}`}
                    />
                    <span className="font-medium text-sm">{alert.title}</span>
                  </div>
                  {alert.body && (
                    <p className="text-xs text-slate-600 mt-1 line-clamp-2">{alert.body}</p>
                  )}
                  <div className="text-xs text-slate-400 mt-1">
                    {formatDate(alert.created_at)}
                  </div>
                </div>
                <button
                  onClick={() => handleAcknowledge(alert.id)}
                  disabled={acknowledging === alert.id}
                  className="shrink-0 bg-white border border-slate-300 text-slate-700 text-xs px-2 py-1 rounded hover:bg-slate-50 disabled:opacity-50 transition-colors"
                >
                  {acknowledging === alert.id ? '...' : 'Ack'}
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
