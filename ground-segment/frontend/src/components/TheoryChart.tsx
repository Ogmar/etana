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

// A thin ring instead of a filled dot — "matches model" is a lighter-weight
// signal than the actual reading itself, so it shouldn't out-weigh it visually.
function MergeMark(props: any) {
  const { cx, cy } = props;
  if (cx == null || cy == null) return <g />;
  return <circle cx={cx} cy={cy} r={3} fill="none" stroke={theme.merge} strokeWidth={1.2} />;
}

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

  // Actual and theoretical are drawn in different colors, but where the
  // balloon's real reading tracks the model closely the two visually merge
  // and it's easy to miss that they agree. Flag those points with a
  // dedicated "merge" color instead of the usual actual-value cyan.
  const { agreeing, diverging } = useMemo(() => {
    const threshold = (yDomain[1] - yDomain[0]) * 0.05;
    const interpTheory = (altitude: number): number | null => {
      if (theory.length === 0) return null;
      if (altitude <= theory[0].altitude) return theory[0].theoretical;
      const last = theory[theory.length - 1];
      if (altitude >= last.altitude) return last.theoretical;
      for (let i = 1; i < theory.length; i++) {
        if (theory[i].altitude >= altitude) {
          const a = theory[i - 1], b = theory[i];
          const span = b.altitude - a.altitude || 1;
          return a.theoretical + (b.theoretical - a.theoretical) * ((altitude - a.altitude) / span);
        }
      }
      return last.theoretical;
    };
    const agree: typeof scatter = [];
    const diverge: typeof scatter = [];
    for (const p of scatter) {
      const tv = interpTheory(p.altitude);
      (tv != null && Math.abs(p.value - tv) <= threshold ? agree : diverge).push(p);
    }
    return { agreeing: agree, diverging: diverge };
  }, [scatter, theory, yDomain]);

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
            <Scatter data={diverging} dataKey="value" fill={theme.cyan} fillOpacity={0.55} />
            <Scatter data={agreeing} dataKey="value" shape={MergeMark} />
            <Line
              data={theory}
              dataKey="theoretical"
              stroke={theme.amber}
              strokeWidth={2}
              strokeDasharray="4 3"
              dot={false}
              isAnimationActive={false}
            />
          </ComposedChart>
        </ResponsiveContainer>
      </div>
      <div className="advcard-legend">
        <span><i className="swatch" style={{ background: theme.cyan }} />actual</span>
        <span><i className="swatch" style={{ background: "transparent", border: `1.2px solid ${theme.merge}` }} />matches model</span>
        <span><i className="swatch" style={{ background: theme.amber }} />theoretical</span>
      </div>
    </div>
  );
}
