import { useEffect, useRef, useState } from "react";
import { api, Sample } from "./api";

export interface LiveState {
  // Latest engineering value per parameter, keyed by name.
  latest: Record<string, number | string | null>;
  // Time series per parameter: {onboard_time, value}[].
  series: Record<string, { t: number; v: number }[]>;
  status: "active" | "complete" | "unknown";
  sampleCount: number;
}

const EMPTY: LiveState = {
  latest: {},
  series: {},
  status: "unknown",
  sampleCount: 0,
};

/**
 * Polls the `since` endpoint every `intervalMs` and accumulates telemetry.
 * Stops polling once the flight is complete and the backlog is drained.
 */
export function useLiveTelemetry(flightId: number | null, intervalMs = 1500) {
  const [state, setState] = useState<LiveState>(EMPTY);
  const cursor = useRef(0);
  const timer = useRef<number | null>(null);

  useEffect(() => {
    // Reset when the selected flight changes.
    cursor.current = 0;
    setState(EMPTY);
    if (flightId == null) return;

    let cancelled = false;

    const poll = async () => {
      try {
        const res = await api.since(flightId, cursor.current);
        if (cancelled) return;
        cursor.current = res.cursor;

        if (res.count > 0) {
          setState((prev) => {
            const latest = { ...prev.latest };
            const series: LiveState["series"] = { ...prev.series };
            for (const s of res.samples) {
              const val = s.engineering_label ?? s.engineering_value;
              latest[s.parameter_name] = val;
              if (typeof s.engineering_value === "number") {
                const arr = series[s.parameter_name]
                  ? series[s.parameter_name].slice()
                  : [];
                arr.push({ t: s.onboard_time, v: s.engineering_value });
                series[s.parameter_name] = arr;
              }
            }
            return {
              latest,
              series,
              status: res.flight_status,
              sampleCount: prev.sampleCount + res.count,
            };
          });
        } else {
          setState((prev) => ({ ...prev, status: res.flight_status }));
        }

        // Keep polling while active, or while complete but still draining.
        const keepGoing = res.flight_status === "active" || res.count > 0;
        if (keepGoing && !cancelled) {
          timer.current = window.setTimeout(poll, intervalMs);
        }
      } catch {
        // On error, retry after the interval (server may be starting).
        if (!cancelled) timer.current = window.setTimeout(poll, intervalMs);
      }
    };

    poll();
    return () => {
      cancelled = true;
      if (timer.current) window.clearTimeout(timer.current);
    };
  }, [flightId, intervalMs]);

  return state;
}

// Convenience: pull a numeric latest value.
export function num(v: number | string | null | undefined): number | null {
  return typeof v === "number" ? v : null;
}

export type { Sample };
