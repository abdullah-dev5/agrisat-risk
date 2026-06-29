import {
  Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  Area, ComposedChart,
} from 'recharts';
import type { BaselinePoint, VegetationReading } from '../types';

interface Props {
  readings: VegetationReading[];
  baseline: BaselinePoint[];
}

const FOREST = '#1B3D36';
const WHEAT = '#B8954A';
const FOREST_MUTED = 'rgba(61, 107, 90, 0.15)';

export function VegetationChart({ readings, baseline }: Props) {
  const nearestBaseline = (day: number) => {
    if (!baseline.length) return undefined;
    return baseline.reduce((best, b) =>
      Math.abs(b.days_since_sowing - day) < Math.abs(best.days_since_sowing - day) ? b : best,
    );
  };

  const chartData = readings.map((r) => {
    const b = nearestBaseline(r.days_since_sowing);
    const value = r.ndvi ?? r.sar_index ?? 0;
    return {
      day: r.days_since_sowing,
      value,
      baselineMean: b?.mean_index,
      baselineUpper: b ? b.mean_index + b.std_index : undefined,
      baselineLower: b ? b.mean_index - b.std_index : undefined,
    };
  });

  return (
    <div className="chart-wrap">
      <ResponsiveContainer width="100%" height={300}>
        <ComposedChart data={chartData} margin={{ top: 8, right: 8, left: -16, bottom: 0 }}>
          <CartesianGrid strokeDasharray="4 4" vertical={false} stroke="rgba(26,26,24,0.06)" />
          <XAxis
            dataKey="day"
            axisLine={false}
            tickLine={false}
            tick={{ fill: '#9C9690', fontSize: 11 }}
            label={{ value: 'Days since sowing', position: 'insideBottom', offset: -2, fill: '#9C9690', fontSize: 11 }}
          />
          <YAxis
            domain={[0, 1]}
            axisLine={false}
            tickLine={false}
            tick={{ fill: '#9C9690', fontSize: 11 }}
            width={36}
          />
          <Tooltip
            contentStyle={{
              background: '#FDFCF9',
              border: '1px solid rgba(26,26,24,0.08)',
              borderRadius: 10,
              fontSize: 12,
              boxShadow: '0 8px 32px rgba(26,61,54,0.08)',
            }}
          />
          <Area type="monotone" dataKey="baselineUpper" stroke="none" fill={FOREST_MUTED} name="Upper band" />
          <Area type="monotone" dataKey="baselineLower" stroke="none" fill="#FDFCF9" name="Lower band" />
          <Line type="monotone" dataKey="baselineMean" stroke={WHEAT} strokeDasharray="6 4" strokeWidth={1.5} dot={false} name="5-yr baseline" />
          <Line type="monotone" dataKey="value" stroke={FOREST} strokeWidth={2.5} dot={{ r: 3, fill: FOREST }} name="This season" />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}
