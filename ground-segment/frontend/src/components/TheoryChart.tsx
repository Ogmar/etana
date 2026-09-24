import { useMemo } from "react";
import {
  CartesianGrid, ComposedChart, Line, ResponsiveContainer, Scatter, Tooltip, XAxis, YAxis,
} from "recharts";
import { joinToAltitude, SeriesPoint } from "../lib/altitudeInterpolation";
import {
  TheoreticalParam, THEORETICAL_LABELS, THEORETICAL_MODELS, THEORETICAL_UNITS,
} from "../lib/theoreticalModel";
import { theme } from "../lib/theme";

interface TheoryChartProps {
  paramKey: TheoreticalParam;
  paramSeries: SeriesPoint[];
  altSeries: SeriesPoint[];
}

const THEORY_SAMPLE_COUNT = 60;

export function TheoryChart({ paramKey, paramSeries, altSeries }: TheoryChartProps) {
  const scatter = useMemo(
    () => joinToAltitude(paramSeries, altSeries).map((p) => ({
      altitude: +(p.altitude / 1000).toFixed(3),
      value: p.value,
    })),
    [paramSeries, altSeries],
  );

  const theory = useMemo(() => {
    const model = THEORETICAL_MODELS[paramKey];
    const observedMax = altSeries.length ? Math.max(...altSeries.map((p) => p.v)) : 0;
    const maxAltM = Math.max(30000, observedMax * 1.02);
    const out: { altitude: number; theoretical: number }[] = [];
    for (let i = 0; i <= THEORY_SAMPLE_COUNT; i++) {
      const altM = (i / THEORY_SAMPLE_COUNT) * maxAltM;
      out.push({ altitude: +(altM / 1000).toFixed(3), theoretical: model(altM) });
    }
    return out;
  }, [paramKey, altSeries]);

  // Compute the Y domain ourselves: Scatter and Line use different dataKeys
  // ("value" vs "theoretical") on a shared axis, so Recharts' implicit
  // per-dataKey domain would only look at one series and could silently
  // clip the other off-chart. Use the 2nd/98th percentile of actual samples
  // (not raw min/max) so a single corrupted decode — a real occurrence on a
  // lossy downlink — doesn't blow out the whole chart's scale.
  const yDomain = useMemo((): [number, number] => {
    const theoryVals = theory.map((p) => p.theoretical);
    const scatterVals = scatter.map((p) => p.value).sort((a, b) => a - b);
    if (!scatterVals.length) {
      const min = Math.min(...theoryVals);
      const max = Math.max(...theoryVals);
      const pad = (max - min) * 0.08 || 1;
      return [min - pad, max + pad];
    }
    const pct = (p: number) => {
      const idx = (scatterVals.length - 1) * p;
      const lo = Math.floor(idx);
      const hi = Math.ceil(idx);
      return lo === hi ? scatterVals[lo] : scatterVals[lo] + (scatterVals[hi] - scatterVals[lo]) * (idx - lo);
    };
    const min = Math.min(pct(0.02), ...theoryVals);
    const max = Math.max(pct(0.98), ...theoryVals);
    const pad = (max - min) * 0.08 || 1;
    return [min - pad, max + pad];
  }, [scatter, theory]);

  return (
    <div className="advcard">
      <h3>
        {THEORETICAL_LABELS[paramKey]}
        <span className="advcard-unit">{THEORETICAL_UNITS[paramKey]} · vs altitude</span>
      </h3>
      <div className="advcard-chart">
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart margin={{ top: 6, right: 10, bottom: 0, left: 0 }}>
            <CartesianGrid stroke={theme.line} strokeDasharray="2 4" />
            <XAxis
              type="number"
              dataKey="altitude"
              domain={["dataMin", "dataMax"]}
              stroke={theme.dim}
              tick={{ fill: theme.muted, fontSize: 10 }}
              tickFormatter={(v: number) => v.toFixed(1)}
              label={{ value: "Altitude (km)", fill: theme.dim, fontSize: 10, position: "insideBottom", offset: -2 }}
            />
            <YAxis
              type="number"
              domain={yDomain}
              stroke={theme.dim}
              tick={{ fill: theme.muted, fontSize: 10 }}
              tickFormatter={(v: number) => v.toFixed(1)}
              width={40}
            />
            <Tooltip
              contentStyle={{
                background: theme.panel, border: `1px solid ${theme.line}`, borderRadius: 4,
                fontSize: 11,
              }}
              labelStyle={{ color: theme.muted }}
            />
            <Scatter data={scatter} dataKey="value" fill={theme.cyan} fillOpacity={0.5} />
            <Line
              data={theory}
              dataKey="theoretical"
              stroke={theme.amber}
              strokeWidth={1.5}
              strokeDasharray="4 3"
              dot={false}
              isAnimationActive={false}
            />
          </ComposedChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
