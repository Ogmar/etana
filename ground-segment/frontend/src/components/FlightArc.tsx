import { useMemo } from "react";

interface Props {
  series: { t: number; v: number }[]; // altitude in metres over onboard time
  burstAltM?: number;
}

/**
 * The signature "flight view": a stylized side profile of the flight as a glowing
 * arc, with the balloon a pulsing dot at the current position. Intuitive for
 * anyone — climb, burst, fall — rendered in the instrument aesthetic.
 */
export function FlightArc({ series, burstAltM = 30000 }: Props) {
  const W = 820;
  const H = 380;
  const padX = 40;
  const padY = 30;
  const groundY = H - padY;

  const { path, dot, peak, maxAlt } = useMemo(() => {
    if (series.length === 0) {
      return { path: "", dot: null as null | { x: number; y: number }, peak: 0, maxAlt: 0 };
    }
    const tMin = series[0].t;
    const tMax = Math.max(series[series.length - 1].t, tMin + 1);
    const aMax = Math.max(burstAltM, ...series.map((p) => p.v)) * 1.05;

    const x = (t: number) => padX + ((t - tMin) / (tMax - tMin)) * (W - 2 * padX);
    const y = (a: number) => groundY - (a / aMax) * (groundY - padY);

    const path = series
      .map((p, i) => `${i === 0 ? "M" : "L"}${x(p.t).toFixed(1)},${y(p.v).toFixed(1)}`)
      .join(" ");

    const last = series[series.length - 1];
    const dot = { x: x(last.t), y: y(last.v) };
    const peak = Math.max(...series.map((p) => p.v));
    return { path, dot, peak, maxAlt: aMax };
  }, [series, burstAltM]);

  const burstY = groundY - (burstAltM / (maxAlt || burstAltM)) * (groundY - padY);

  return (
    <svg viewBox={`0 0 ${W} ${H}`} width="100%" height="100%" preserveAspectRatio="xMidYMid meet">
      <defs>
        <linearGradient id="arcFill" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#00e5c7" stopOpacity="0.25" />
          <stop offset="100%" stopColor="#00e5c7" stopOpacity="0" />
        </linearGradient>
        <filter id="glow">
          <feGaussianBlur stdDeviation="3" result="b" />
          <feMerge>
            <feMergeNode in="b" />
            <feMergeNode in="SourceGraphic" />
          </feMerge>
        </filter>
      </defs>

      {/* ground line */}
      <line x1={padX} y1={groundY} x2={W - padX} y2={groundY} stroke="#1b2632" strokeWidth="1" />
      <text x={padX} y={groundY + 16} fill="#4a5765" fontSize="10" fontFamily="var(--mono)">
        GROUND
      </text>

      {/* burst altitude marker */}
      {maxAlt > 0 && (
        <>
          <line
            x1={padX}
            y1={burstY}
            x2={W - padX}
            y2={burstY}
            stroke="#ffb020"
            strokeWidth="1"
            strokeDasharray="4 5"
            opacity="0.5"
          />
          <text x={W - padX} y={burstY - 6} fill="#ffb020" fontSize="10" textAnchor="end" fontFamily="var(--mono)" opacity="0.8">
            BURST {(burstAltM / 1000).toFixed(0)} km
          </text>
        </>
      )}

      {/* filled area under the arc */}
      {path && (
        <path d={`${path} L${dot?.x ?? padX},${groundY} L${padX},${groundY} Z`} fill="url(#arcFill)" />
      )}

      {/* the arc */}
      {path && <path d={path} fill="none" stroke="#00e5c7" strokeWidth="2" filter="url(#glow)" />}

      {/* the balloon */}
      {dot && (
        <g filter="url(#glow)">
          <circle cx={dot.x} cy={dot.y} r="7" fill="#05070a" stroke="#00e5c7" strokeWidth="2" />
          <circle cx={dot.x} cy={dot.y} r="3" fill="#00e5c7">
            <animate attributeName="opacity" values="1;0.3;1" dur="1.4s" repeatCount="indefinite" />
          </circle>
        </g>
      )}

      {/* current altitude label near the balloon */}
      {dot && (
        <text
          x={dot.x}
          y={dot.y - 14}
          fill="#00e5c7"
          fontSize="12"
          textAnchor="middle"
          fontFamily="var(--mono)"
          fontWeight="500"
        >
          {(peak >= 0 ? series[series.length - 1].v / 1000 : 0).toFixed(1)} km
        </text>
      )}
    </svg>
  );
}
