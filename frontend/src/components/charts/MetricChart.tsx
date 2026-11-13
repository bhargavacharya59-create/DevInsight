import {
  ResponsiveContainer, LineChart, Line, XAxis, YAxis,
  CartesianGrid, Tooltip, ReferenceLine,
} from 'recharts';
import { format, parseISO } from 'date-fns';
import type { MetricDataPoint } from '../../types';

interface MetricChartProps {
  data: MetricDataPoint[];
  label: string;
  unit?: string;
  color?: string;
  height?: number;
  thresholdValue?: number;
  anomalyMarkers?: string[];
  mini?: boolean;
}

const CustomTooltip = ({ active, payload, label, unit }: {
  active?: boolean; payload?: Array<{ value: number }>; label?: string; unit?: string;
}) => {
  if (!active || !payload?.length) return null;
  return (
    <div className="bg-surface-700 border border-slate-600/50 rounded-lg p-3 text-xs shadow-xl">
      <p className="text-slate-400 mb-1">{label}</p>
      <p className="text-white font-semibold">{payload[0].value.toFixed(2)} {unit}</p>
    </div>
  );
};

export default function MetricChart({
  data, label, unit = '', color = '#6366f1',
  height = 200, thresholdValue, anomalyMarkers, mini = false,
}: MetricChartProps) {
  const formatted = data.map(d => ({
    ...d,
    time: format(parseISO(d.timestamp), 'HH:mm'),
  }));

  if (mini) {
    return (
      <ResponsiveContainer width="100%" height={60}>
        <LineChart data={formatted} margin={{ top: 2, right: 2, bottom: 2, left: 2 }}>
          <Line type="monotone" dataKey="value" stroke={color} strokeWidth={1.5} dot={false} />
        </LineChart>
      </ResponsiveContainer>
    );
  }

  return (
    <div>
      {label && <p className="text-sm text-slate-400 mb-2">{label}</p>}
      <ResponsiveContainer width="100%" height={height}>
        <LineChart data={formatted} margin={{ top: 5, right: 10, bottom: 5, left: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#1a2342" vertical={false} />
          <XAxis
            dataKey="time"
            tick={{ fill: '#64748b', fontSize: 11 }}
            tickLine={false}
            axisLine={false}
            interval="preserveStartEnd"
          />
          <YAxis
            tick={{ fill: '#64748b', fontSize: 11 }}
            tickLine={false}
            axisLine={false}
            width={45}
            tickFormatter={v => `${v}${unit}`}
          />
          <Tooltip content={<CustomTooltip unit={unit} />} />
          {thresholdValue && (
            <ReferenceLine
              y={thresholdValue}
              stroke="#ef4444"
              strokeDasharray="4 4"
              strokeWidth={1}
            />
          )}
          {anomalyMarkers?.map((ts, i) => (
            <ReferenceLine
              key={i}
              x={format(parseISO(ts), 'HH:mm')}
              stroke="#f97316"
              strokeDasharray="2 2"
              strokeWidth={1}
            />
          ))}
          <Line
            type="monotone"
            dataKey="value"
            stroke={color}
            strokeWidth={2}
            dot={false}
            activeDot={{ r: 4, fill: color }}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
