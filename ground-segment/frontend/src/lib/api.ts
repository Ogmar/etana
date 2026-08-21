// Typed client for the Etana telemetry API.

export interface Flight {
  id: number;
  name: string;
  started_at: string;
  ended_at: string | null;
  status: "active" | "complete";
  source: string;
  notes: string;
  packet_count: number;
}

export interface Sample {
  id: number;
  parameter_name: string;
  onboard_time: number;
  received_at: string;
  raw_value: number;
  engineering_value: number | null;
  engineering_label: string | null;
}

export interface SinceResponse {
  flight_id: number;
  flight_status: "active" | "complete";
  since: number;
  cursor: number;
  count: number;
  samples: Sample[];
}

export interface TrackPoint {
  onboard_time: number;
  lat: number;
  lon: number;
  altitude: number | null;
}

export interface LossRow {
  apid: number;
  lost_count: number;
  event_count: number;
}

export interface FlightEvent {
  onboard_time: number | null;
  received_at: string;
  event: string;
}

const BASE = "/api";

async function getJSON<T>(url: string): Promise<T> {
  const res = await fetch(url, { headers: { Accept: "application/json" } });
  if (!res.ok) throw new Error(`${url} -> ${res.status}`);
  return res.json() as Promise<T>;
}

export const api = {
  flights: () => getJSON<Flight[]>(`${BASE}/flights/`),
  flight: (id: number) => getJSON<Flight>(`${BASE}/flights/${id}/`),
  since: (id: number, cursor: number) =>
    getJSON<SinceResponse>(`${BASE}/flights/${id}/since/?since=${cursor}`),
  track: (id: number) =>
    getJSON<{ points: TrackPoint[] }>(`${BASE}/flights/${id}/track/`),
  loss: (id: number) => getJSON<LossRow[]>(`${BASE}/flights/${id}/loss/`),
  events: (id: number) => getJSON<FlightEvent[]>(`${BASE}/flights/${id}/events/`),
};

// APID -> human label, for loss badges.
export const APID_NAMES: Record<number, string> = {
  100: "GPS",
  200: "PAYLOAD",
  300: "HOUSEKEEPING",
  400: "EVENTS",
};
