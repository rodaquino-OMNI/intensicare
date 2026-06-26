import type { PatientBedSummary } from '../types';

interface BedCardProps {
  patient: PatientBedSummary;
  onClick: (mpiId: string) => void;
}

function TrendIcon({ trend }: { trend: string | null }) {
  if (!trend) return <span className="text-gray-400">→</span>;
  if (trend === 'increasing') return <span className="text-red-500 font-bold">↑</span>;
  if (trend === 'decreasing') return <span className="text-green-500 font-bold">↓</span>;
  return <span className="text-gray-500">→</span>;
}

function AlertBadge({ severity }: { severity: string | null }) {
  if (!severity) return <span className="inline-block w-3 h-3 rounded-full bg-green-400" />;
  if (severity === 'critical')
    return <span className="inline-block w-3 h-3 rounded-full bg-red-500 animate-pulse" />;
  if (severity === 'warning')
    return <span className="inline-block w-3 h-3 rounded-full bg-yellow-500" />;
  return <span className="inline-block w-3 h-3 rounded-full bg-blue-400" />;
}

function ScoreValue({ score, risk, label }: { score: number | null; risk: string | null; label: string }) {
  if (score === null || score === undefined)
    return <span className="text-gray-400 text-xs">--</span>;

  let color = 'text-gray-700';
  if (label === 'MEWS') {
    if (score >= 5) color = 'text-red-600 font-bold';
    else if (score >= 3) color = 'text-yellow-600 font-semibold';
  } else {
    if (risk === 'high') color = 'text-red-600 font-bold';
    else if (risk === 'medium') color = 'text-yellow-600 font-semibold';
  }

  return (
    <span className={`text-sm ${color}`}>
      {score}
      {risk && risk !== 'low' && (
        <span className="text-xs ml-1 opacity-70">({risk})</span>
      )}
    </span>
  );
}

export default function BedCard({ patient, onClick }: BedCardProps) {
  const hasAlerts = patient.active_alerts_count > 0;

  return (
    <button
      onClick={() => onClick(patient.mpi_id)}
      className={`w-full text-left bg-white rounded-lg border-2 p-4 hover:shadow-md transition-shadow focus:outline-none focus:ring-2 focus:ring-blue-500 ${
        patient.highest_alert_severity === 'critical'
          ? 'border-red-300 bg-red-50'
          : hasAlerts
            ? 'border-yellow-300 bg-yellow-50'
            : 'border-gray-200'
      }`}
    >
      <div className="flex items-center justify-between mb-2">
        <div>
          <div className="flex items-center gap-2">
            <AlertBadge severity={patient.highest_alert_severity} />
            <span className="font-semibold text-slate-800 text-sm">
              {patient.display_name}
            </span>
          </div>
          <div className="text-xs text-slate-500 mt-0.5">
            {patient.bed_id ? `Bed ${patient.bed_id}` : 'No bed'}
            {patient.unit && ` · ${patient.unit}`}
          </div>
        </div>
        {patient.active_alerts_count > 0 && (
          <span className="bg-red-500 text-white text-xs font-bold px-2 py-0.5 rounded-full">
            {patient.active_alerts_count}
          </span>
        )}
      </div>

      <div className="grid grid-cols-2 gap-2 text-xs">
        <div>
          <span className="text-slate-500">MEWS</span>
          <div className="flex items-center gap-1">
            <ScoreValue score={patient.latest_mews} risk={null} label="MEWS" />
            <TrendIcon trend={patient.mews_trend} />
          </div>
        </div>
        <div>
          <span className="text-slate-500">NEWS2</span>
          <div className="flex items-center gap-1">
            <ScoreValue score={patient.latest_news2} risk={patient.news2_risk} label="NEWS2" />
            <TrendIcon trend={patient.news2_trend} />
          </div>
        </div>
      </div>
    </button>
  );
}
