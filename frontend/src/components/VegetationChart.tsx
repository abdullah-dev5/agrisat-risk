import {
  Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
  Area, ComposedChart,
} from 'recharts';
import type { BaselinePoint, VegetationReading } from '../types';
import { TIER_LABELS } from '../lib/constants';

interface Props {
  readings: VegetationReading[];
  baseline: BaselinePoint[];
}

export function VegetationChart({ readings, baseline }: Props) {
  const chartData = readings.map((r) => {
    const b = baseline.find((x) => x.days_since_sowing === r.days_since_sowing);
    const value = r.ndvi ?? r.sar_index ?? 0;
    return {
      day: r.days_since_sowing,
      value,
      tier: TIER_LABELS[r.data_tier] ?? r.data_tier,
      baselineMean: b?.mean_index,
      baselineUpper: b ? b.mean_index + b.std_index : undefined,
      baselineLower: b ? b.mean_index - b.std_index : undefined,
    };
  });

  return (
    <ResponsiveContainer width="100%" height={320}>
      <ComposedChart data={chartData}>
        <CartesianGrid strokeDasharray="3 3" stroke="#475569" />
        <XAxis dataKey="day" label={{ value: 'Days since sowing', position: 'insideBottom', offset: -5 }} />
        <YAxis domain={[0, 1]} />
        <Tooltip />
        <Legend />
        <Area type="monotone" dataKey="baselineUpper" stroke="none" fill="#166534" fillOpacity={0.15} name="Baseline +1σ" />
        <Area type="monotone" dataKey="baselineLower" stroke="none" fill="#0f172a" fillOpacity={1} name="Baseline -1σ" />
        <Line type="monotone" dataKey="baselineMean" stroke="#4ade80" strokeDasharray="4 4" dot={false} name="5-yr baseline" />
        <Line type="monotone" dataKey="value" stroke="#38bdf8" strokeWidth={2} dot={{ r: 3 }} name="Current season" />
      </ComposedChart>
    </ResponsiveContainer>
  );
}
