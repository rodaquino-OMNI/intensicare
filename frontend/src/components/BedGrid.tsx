import { useEffect, useState, useCallback } from 'react';
import { apiClient } from '../api/client';
import type { PatientBedSummary } from '../types';
import BedCard from './BedCard';

interface BedGridProps {
  onSelectPatient: (mpiId: string) => void;
}

export default function BedGrid({ onSelectPatient }: BedGridProps) {
  const [patients, setPatients] = useState<PatientBedSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [totalAlerts, setTotalAlerts] = useState(0);

  const fetchDashboard = useCallback(async () => {
    try {
      setError(null);
      const data = await apiClient.getDashboard();
      setPatients(data.patients || []);
      setTotalAlerts(data.active_alerts_total || 0);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load dashboard');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchDashboard();
    const interval = setInterval(fetchDashboard, 30000); // Refresh every 30s
    return () => clearInterval(interval);
  }, [fetchDashboard]);

  // Sort: critical alerts first, then warning, then by bed_id
  const sorted = [...patients].sort((a, b) => {
    const sevOrder = (s: string | null) => {
      if (s === 'critical') return 0;
      if (s === 'warning') return 1;
      return 2;
    };
    const sa = sevOrder(a.highest_alert_severity);
    const sb = sevOrder(b.highest_alert_severity);
    if (sa !== sb) return sa - sb;
    return (a.bed_id || '') > (b.bed_id || '') ? 1 : -1;
  });

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-slate-500">Loading patient data...</div>
      </div>
    );
  }

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-xl font-bold text-slate-800">Patient Bed Grid</h2>
          <p className="text-sm text-slate-500 mt-0.5">
            {patients.length} patients
            {totalAlerts > 0 && (
              <span className="text-red-600 font-semibold"> · {totalAlerts} active alerts</span>
            )}
          </p>
        </div>
        <button
          onClick={fetchDashboard}
          className="text-sm text-blue-600 hover:text-blue-800 transition-colors"
        >
          Refresh
        </button>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded mb-4 text-sm">
          {error}
        </div>
      )}

      {patients.length === 0 ? (
        <div className="text-center py-12 text-slate-400">
          No patients found. Connect monitors to begin receiving data.
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-3">
          {sorted.map((p) => (
            <BedCard key={p.mpi_id} patient={p} onClick={onSelectPatient} />
          ))}
        </div>
      )}
    </div>
  );
}
