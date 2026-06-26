import type { ScoreHistoryPoint } from '../types';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';

interface ScoreTrendChartProps {
  mewsHistory: ScoreHistoryPoint[];
  news2History: ScoreHistoryPoint[];
}

export default function ScoreTrendChart({ mewsHistory, news2History }: ScoreTrendChartProps) {
  // Create a merged timeline
  const allTimes = new Set<string>();

  const mewsMap = new Map<string, number>();
  mewsHistory.forEach((s) => {
    const t = new Date(s.calculated_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    mewsMap.set(t, s.score_value);
    allTimes.add(t);
  });

  const news2Map = new Map<string, number>();
  news2History.forEach((s) => {
    const t = new Date(s.calculated_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    news2Map.set(t, s.score_value);
    allTimes.add(t);
  });

  const chartData = Array.from(allTimes)
    .sort()
    .map((t) => ({
      time: t,
      MEWS: mewsMap.get(t) ?? null,
      NEWS2: news2Map.get(t) ?? null,
    }));

  if (chartData.length === 0) {
    return (
      <div className="text-center py-8 text-slate-400 text-sm">
        No score data available
      </div>
    );
  }

  return (
    <div className="w-full h-48">
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
          <Line
            type="monotone"
            dataKey="MEWS"
            stroke="#f59e0b"
            strokeWidth={3}
            dot={{ r: 2 }}
            connectNulls
          />
          <Line
            type="monotone"
            dataKey="NEWS2"
            stroke="#8b5cf6"
            strokeWidth={3}
            dot={{ r: 2 }}
            connectNulls
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
