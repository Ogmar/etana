import {
  CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";
import { theme } from "../lib/theme";

interface TimeSeriesChartProps {
  label: string;
  unit?: string;
  data: { t: number; v: number }[];
  curveType?: "monotone" | "stepAfter";
}

export function TimeSeriesChart({ label, unit, data, curveType = "monotone" }: TimeSeriesChartProps) {
  const chartData = data.map((p) => ({ t: +(p.t / 60).toFixed(2), v: p.v }));
  return (
    <div className="advcard">
      <h3>
        {label}
        {unit && <span className="advcard-unit">{unit}</span>}
      </h3>
      <div className="advcard-chart">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={chartData} margin={{ top: 6, right: 10, bottom: 0, left: 0 }}>
            <CartesianGrid stroke={theme.line} strokeDasharray="2 4" />
            <XAxis
              dataKey="t"
              stroke={theme.dim}
              tick={{ fill: theme.muted, fontSize: 10 }}
            />
            <YAxis stroke={theme.dim} tick={{ fill: theme.muted, fontSize: 10 }} width={40} />
            <Tooltip
              contentStyle={{
                background: theme.panel, border: `1px solid ${theme.line}`, borderRadius: 4,
                fontSize: 11,
              }}
              labelStyle={{ color: theme.muted }}
            />
            <Line type={curveType} dataKey="v" stroke={theme.cyan} strokeWidth={1.5} dot={false} isAnimationActive={false} />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
