export interface SeriesPoint {
  t: number;
  v: number;
}

/**
 * Linearly interpolates altitude at time t between the bracketing samples in
 * altSeries (assumed sorted ascending by t — true for useLiveTelemetry's
 * append-only accumulation). Clamps to the nearest endpoint outside range;
 * returns null only when altSeries is empty.
 */
export function interpolateAtTime(altSeries: SeriesPoint[], t: number): number | null {
  const n = altSeries.length;
  if (n === 0) return null;
  if (t <= altSeries[0].t) return altSeries[0].v;
  if (t >= altSeries[n - 1].t) return altSeries[n - 1].v;

  let lo = 0;
  let hi = n - 1;
  while (hi - lo > 1) {
    const mid = (lo + hi) >> 1;
    if (altSeries[mid].t <= t) lo = mid;
    else hi = mid;
  }
  const a = altSeries[lo];
  const b = altSeries[hi];
  if (b.t === a.t) return a.v;
  return a.v + ((t - a.t) / (b.t - a.t)) * (b.v - a.v);
}

/**
 * Joins a parameter's own-cadence samples to interpolated altitude at each
 * sample's onboard_time — for altitude-vs-parameter comparison charts.
 */
export function joinToAltitude(
  paramSeries: SeriesPoint[],
  altSeries: SeriesPoint[],
): { altitude: number; value: number; t: number }[] {
  const out: { altitude: number; value: number; t: number }[] = [];
  for (const p of paramSeries) {
    const alt = interpolateAtTime(altSeries, p.t);
    if (alt != null) out.push({ altitude: alt, value: p.v, t: p.t });
  }
  return out;
}
