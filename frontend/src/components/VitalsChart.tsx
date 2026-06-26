import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts';
import type { VitalsHistoryPoint } from '../types';

interface VitalsChartProps {
  data: VitalsHistoryPoint[];
}

const COLORS: Record<string, string> = {
  heart_rate: '#ef4444',
  systolic_bp: '#3b82f6',
  diastolic_bp: '#93c5fd',
  spo2: '#10b981',
  respiratory_rate: '#f59e0b',
  temperature: '#8b5cf6',
};

export default function VitalsChart({ data }: VitalsChartProps) {
  if (!data || data.length === 0) {
    return (
      <div className="text-center py-8 text-slate-400 text-sm">
        No vitals data available for the last 24 hours
      </div>
    );
  }

  const chartData = data.map((d) => ({
    time: new Date(d.recorded_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    heart_rate: d.heart_rate,
    systolic_bp: d.systolic_bp,
    diastolic_bp: d.diastolic_bp,
    spo2: d.spo2,
    respiratory_rate: d.respiratory_rate,
    temperature: d.temperature,
  }));

  return (
    <div className="w-full h-64">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={chartData} margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
          <XAxis
            dataKey="time"
            tick={{ fontSize: 11, fill: '#6b7280' }}
            interval="preserveStartEnd"
          />
          <YAxis tick={{ fontSize: 11, fill: '#6b7280' }} />
          <Tooltip
            contentStyle={{
              background: '#fff',
              border: '1px solid #e5e7eb',
              borderRadius: '6px',
              fontSize: '12px',
            }}
          />
          <Legend wrapperStyle={{ fontSize: '12px' }} />
          <Line
            type="monotone"
            dataKey="heart_rate"
            stroke={COLORS.heart_rate}
            name="HR"
            dot={false}
            strokeWidth={2}
          />
          <Line
            type="monotone"
            dataKey="systolic_bp"
            stroke={COLORS.systolic_bp}
            name="SBP"
            dot={false}
            strokeWidth={2}
          />
          <Line
            type="monotone"
            dataKey="spo2"
            stroke={COLORS.spo2}
            name="SpO₂"
            dot={false}
            strokeWidth={2}
          />
          <Line
            type="monotone"
            dataKey="respiratory_rate"
            stroke={COLORS.respiratory_rate}
            name="RR"
            dot={false}
            strokeWidth={2}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
