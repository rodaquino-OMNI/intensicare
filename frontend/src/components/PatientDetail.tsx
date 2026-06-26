import { useEffect, useState, useCallback } from 'react';
import { apiClient } from '../api/client';
import type { PatientDetailResponse } from '../types';
import VitalsChart from './VitalsChart';
import ScoreTrendChart from './ScoreTrendChart';
import AlertPanel from './AlertPanel';

interface PatientDetailProps {
  mpiId: string;
  onBack: () => void;
}

export default function PatientDetail({ mpiId, onBack }: PatientDetailProps) {
  const [data, setData] = useState<PatientDetailResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [tab, setTab] = useState<'vitals' | 'scores' | 'alerts'>('vitals');

  const fetchDetail = useCallback(async () => {
    try {
      setError(null);
      const result = await apiClient.getPatientDetail(mpiId);
      setData(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load patient data');
    } finally {
      setLoading(false);
    }
  }, [mpiId]);

  useEffect(() => {
    setLoading(true);
    fetchDetail();
    const interval = setInterval(fetchDetail, 15000);
    return () => clearInterval(interval);
  }, [fetchDetail]);

  if (loading) {
    return (
      <div className="p-6 flex items-center justify-center h-64">
        <div className="text-slate-500">Loading patient data...</div>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="p-6">
        <button onClick={onBack} className="text-blue-600 hover:text-blue-800 text-sm mb-4">
          ← Back to Grid
        </button>
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded text-sm">
          {error || 'Patient not found'}
        </div>
      </div>
    );
  }

  const tabs = [
    { key: 'vitals' as const, label: 'Vitals' },
    { key: 'scores' as const, label: 'Scores' },
    { key: 'alerts' as const, label: `Alerts (${data.active_alerts.filter((a) => a.status === 'active').length})` },
  ];

  return (
    <div className="p-6 max-w-5xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <button onClick={onBack} className="text-blue-600 hover:text-blue-800 text-sm mb-1">
            ← Back to Grid
          </button>
          <h2 className="text-xl font-bold text-slate-800">{data.display_name}</h2>
          <p className="text-sm text-slate-500">
            {data.bed_id ? `Bed ${data.bed_id}` : 'No bed'}
            {data.unit && ` · ${data.unit}`}
            <span className="ml-2 text-slate-400">MPI: {data.mpi_id}</span>
          </p>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 border-b border-slate-200 mb-4">
        {tabs.map((t) => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            className={`px-4 py-2 text-sm font-medium transition-colors border-b-2 -mb-px ${
              tab === t.key
                ? 'border-blue-500 text-blue-600'
                : 'border-transparent text-slate-500 hover:text-slate-700'
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      {tab === 'vitals' && (
        <div className="bg-white rounded-lg border border-slate-200 p-4">
          <h3 className="font-semibold text-slate-800 mb-3">Vital Signs (24h)</h3>
          <VitalsChart data={data.vitals_history} />

          {/* Latest vitals summary */}
          {data.vitals_history.length > 0 && (
            <div className="grid grid-cols-3 sm:grid-cols-4 md:grid-cols-7 gap-2 mt-4 text-xs">
              {[
                { label: 'HR', value: data.vitals_history[data.vitals_history.length - 1]?.heart_rate, unit: 'bpm', color: 'text-red-600' },
                { label: 'SBP', value: data.vitals_history[data.vitals_history.length - 1]?.systolic_bp, unit: 'mmHg', color: 'text-blue-600' },
                { label: 'DBP', value: data.vitals_history[data.vitals_history.length - 1]?.diastolic_bp, unit: 'mmHg', color: 'text-blue-400' },
                { label: 'SpO₂', value: data.vitals_history[data.vitals_history.length - 1]?.spo2, unit: '%', color: 'text-green-600' },
                { label: 'RR', value: data.vitals_history[data.vitals_history.length - 1]?.respiratory_rate, unit: 'rpm', color: 'text-amber-600' },
                { label: 'Temp', value: data.vitals_history[data.vitals_history.length - 1]?.temperature, unit: '°C', color: 'text-purple-600' },
                { label: 'AVPU', value: data.vitals_history[data.vitals_history.length - 1]?.avpu, unit: '', color: 'text-slate-600' },
              ].map((item) => (
                <div key={item.label} className="bg-slate-50 rounded p-2 text-center">
                  <div className="text-slate-400">{item.label}</div>
                  <div className={`font-bold text-sm ${item.color}`}>
                    {item.value ?? '--'}{item.unit}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {tab === 'scores' && (
        <div className="bg-white rounded-lg border border-slate-200 p-4">
          <h3 className="font-semibold text-slate-800 mb-3">Score Trends (24h)</h3>
          <ScoreTrendChart mewsHistory={data.mews_history} news2History={data.news2_history} />

          {/* Latest scores */}
          <div className="grid grid-cols-2 gap-4 mt-4">
            <div className="bg-amber-50 rounded-lg p-3 border border-amber-200">
              <div className="text-xs text-amber-600 font-medium mb-1">MEWS</div>
              <div className="text-2xl font-bold text-amber-700">
                {data.mews_history.length > 0
                  ? data.mews_history[data.mews_history.length - 1].score_value
                  : '--'}
              </div>
              {data.mews_history.length > 0 && (
                <div className="text-xs text-amber-500 mt-1">
                  Trend: {data.mews_history[data.mews_history.length - 1].trend || 'stable'}
                </div>
              )}
            </div>
            <div className="bg-purple-50 rounded-lg p-3 border border-purple-200">
              <div className="text-xs text-purple-600 font-medium mb-1">NEWS2</div>
              <div className="text-2xl font-bold text-purple-700">
                {data.news2_history.length > 0
                  ? data.news2_history[data.news2_history.length - 1].score_value
                  : '--'}
              </div>
              {data.news2_history.length > 0 && (
                <div className="text-xs text-purple-500 mt-1">
                  Trend: {data.news2_history[data.news2_history.length - 1].trend || 'stable'}
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {tab === 'alerts' && (
        <div className="bg-white rounded-lg border border-slate-200 p-4">
          <AlertPanel alerts={data.active_alerts} onAcknowledged={fetchDetail} />
        </div>
      )}
    </div>
  );
}
