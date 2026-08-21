import { useEffect, useMemo, useState } from "react";
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from "recharts";
import { api, APID_NAMES, Flight, FlightEvent, LossRow } from "./lib/api";
import { useLiveTelemetry, num } from "./lib/useLiveTelemetry";
import { FlightArc } from "./components/FlightArc";

type Mode = "flight" | "mission";

export default function App() {
  const [flights, setFlights] = useState<Flight[]>([]);
  const [flightId, setFlightId] = useState<number | null>(null);
  const [mode, setMode] = useState<Mode>("flight");
  const [loss, setLoss] = useState<LossRow[]>([]);
  const [events, setEvents] = useState<FlightEvent[]>([]);

  const live = useLiveTelemetry(flightId);

  // Load flight list on mount; auto-select the newest.
  useEffect(() => {
    api.flights().then((fs) => {
      setFlights(fs);
      if (fs.length && flightId == null) setFlightId(fs[0].id);
    }).catch(() => {});
  }, []);

  // Refresh loss + events periodically while a flight is selected.
  useEffect(() => {
    if (flightId == null) return;
    const load = () => {
      api.loss(flightId).then(setLoss).catch(() => {});
      api.events(flightId).then(setEvents).catch(() => {});
    };
    load();
    const iv = window.setInterval(load, 3000);
    return () => window.clearInterval(iv);
  }, [flightId]);

  const flight = flights.find((f) => f.id === flightId) || null;
  const altSeries = live.series["gps_altitude"] ?? [];

  const alt = num(live.latest["gps_altitude"]);
  const lat = num(live.latest["gps_latitude"]);
  const lon = num(live.latest["gps_longitude"]);
  const ozone = num(live.latest["ozone_raw"]);
  const co2 = num(live.latest["co2_raw"]);
  const battery = num(live.latest["battery"]);
  const tempIn = num(live.latest["temp_internal"]);
  const tempOut = num(live.latest["temp_external"]);
  const sats = num(live.latest["gps_sats"]);
  const fix = live.latest["gps_fix"];

  const missionClock = useMemo(() => {
    const t = altSeries.length ? altSeries[altSeries.length - 1].t : 0;
    const m = Math.floor(t / 60), s = Math.floor(t % 60);
    return `T+${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
  }, [altSeries]);

  return (
    <div className="console">
      <div className="statusbar">
        <div className="brand">ETANA<span>·</span>MISSION CONSOLE</div>

        <select
          className="flightsel"
          value={flightId ?? ""}
          onChange={(e) => setFlightId(Number(e.target.value))}
        >
          {flights.length === 0 && <option value="">no flights</option>}
          {flights.map((f) => (
            <option key={f.id} value={f.id}>
              #{f.id} {f.name || "unnamed"} · {f.packet_count} pkt
            </option>
          ))}
        </select>

        <div className="modetoggle">
          <button className={mode === "flight" ? "on" : ""} onClick={() => setMode("flight")}>
            FLIGHT
          </button>
          <button className={mode === "mission" ? "on" : ""} onClick={() => setMode("mission")}>
            MISSION
          </button>
        </div>

        <div className="sep" />

        <div className="clock">
          <span className="label">MISSION TIME</span>
          {missionClock}
        </div>

        <StatusChip status={live.status} />
      </div>

      <div className="main">
        <div className="stage">
          {flight == null ? (
            <div className="empty">
              <div className="big">◇</div>
              No flight selected. Run a flight, then reload.
            </div>
          ) : mode === "flight" ? (
            <FlightMode altSeries={altSeries} alt={alt} clock={missionClock} status={live.status} />
          ) : (
            <MissionMode altSeries={altSeries} />
          )}
        </div>

        <div className="rail">
          <div className="panel">
            <h2>Position</h2>
            <Readout k="Altitude" v={alt != null ? (alt / 1000).toFixed(2) : "—"} u="km" hot />
            <Readout k="Latitude" v={lat != null ? lat.toFixed(4) : "—"} u="°" />
            <Readout k="Longitude" v={lon != null ? lon.toFixed(4) : "—"} u="°" />
            <Readout k="GPS fix" v={typeof fix === "string" ? fix : "—"} />
            <Readout k="Satellites" v={sats != null ? String(sats) : "—"} />
          </div>

          <div className="panel">
            <h2>Payload</h2>
            <Readout k="Ozone" v={ozone != null ? ozone.toFixed(1) : "—"} u="ppb" hot />
            <Readout k="CO₂" v={co2 != null ? co2.toFixed(0) : "—"} u="ppm" />
            <Readout k="Battery" v={battery != null ? battery.toFixed(2) : "—"} u="V" />
            <Readout k="Temp (int)" v={tempIn != null ? tempIn.toFixed(1) : "—"} u="°C" />
            <Readout k="Temp (ext)" v={tempOut != null ? tempOut.toFixed(1) : "—"} u="°C" />
          </div>

          <div className="panel">
            <h2>Packet loss</h2>
            <LossBadges loss={loss} />
          </div>

          <div className="panel">
            <h2>Event log</h2>
            <EventLog events={events} />
          </div>
        </div>
      </div>
    </div>
  );
}

function StatusChip({ status }: { status: string }) {
  const cls = status === "active" ? "live" : status === "complete" ? "complete" : "";
  const label = status === "active" ? "LIVE" : status === "complete" ? "COMPLETE" : "IDLE";
  return (
    <div className={`livechip ${cls}`}>
      <span className="dot" />
      {label}
    </div>
  );
}

function Readout({ k, v, u, hot }: { k: string; v: string; u?: string; hot?: boolean }) {
  return (
    <div className="readout">
      <span className="k">{k}</span>
      <span className={`v ${hot ? "hot" : ""}`}>
        {v}
        {u && <span className="u">{u}</span>}
      </span>
    </div>
  );
}

function LossBadges({ loss }: { loss: LossRow[] }) {
  const byApid: Record<number, number> = {};
  for (const r of loss) byApid[r.apid] = r.lost_count;
  const apids = [100, 200, 300, 400];
  return (
    <div className="badges">
      {apids.map((a) => {
        const lost = byApid[a] ?? 0;
        return (
          <div key={a} className={`badge ${lost > 0 ? "lossy" : "clean"}`}>
            <span className="name">{APID_NAMES[a]}</span>
            <span className="count">{lost}</span>
          </div>
        );
      })}
    </div>
  );
}

function EventLog({ events }: { events: FlightEvent[] }) {
  if (events.length === 0) return <div style={{ color: "var(--dim)", fontFamily: "var(--mono)", fontSize: 12 }}>awaiting events…</div>;
  return (
    <div className="eventlog">
      {events.map((e, i) => {
        const t = e.onboard_time ?? 0;
        const m = Math.floor(t / 60), s = t % 60;
        return (
          <div className="eventrow" key={i}>
            <span className="t">T+{String(m).padStart(2, "0")}:{String(s).padStart(2, "0")}</span>
            <span className="e">{e.event.replace(/_/g, " ")}</span>
          </div>
        );
      })}
    </div>
  );
}

function FlightMode({
  altSeries, alt, clock, status,
}: {
  altSeries: { t: number; v: number }[];
  alt: number | null;
  clock: string;
  status: string;
}) {
  const peak = altSeries.length ? Math.max(...altSeries.map((p) => p.v)) : 0;
  return (
    <div className="arcstage">
      <div className="stage-head" style={{ padding: 0 }}>
        <h1>Flight profile</h1>
        <p>{status === "active" ? "tracking live" : status === "complete" ? "flight complete" : "standby"}</p>
      </div>
      <div style={{ flex: 1, minHeight: 0, marginTop: 12 }}>
        <FlightArc series={altSeries} />
      </div>
      <div className="arc-metrics">
        <div className="arc-metric">
          <div className="val">{alt != null ? (alt / 1000).toFixed(1) : "0.0"}</div>
          <div className="lab">Altitude km</div>
        </div>
        <div className="arc-metric">
          <div className="val">{(peak / 1000).toFixed(1)}</div>
          <div className="lab">Peak km</div>
        </div>
        <div className="arc-metric">
          <div className="val">{clock}</div>
          <div className="lab">Elapsed</div>
        </div>
      </div>
    </div>
  );
}

function MissionMode({ altSeries }: { altSeries: { t: number; v: number }[] }) {
  const data = altSeries.map((p) => ({ t: +(p.t / 60).toFixed(2), alt: +(p.v / 1000).toFixed(2) }));
  return (
    <>
      <div className="stage-head">
        <h1>Telemetry · Altitude</h1>
        <p>engineering units · onboard time</p>
      </div>
      <div className="chart-wrap" style={{ height: 340 }}>
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data} margin={{ top: 10, right: 20, bottom: 10, left: 0 }}>
            <CartesianGrid stroke="#1b2632" strokeDasharray="2 4" />
            <XAxis
              dataKey="t"
              stroke="#4a5765"
              tick={{ fill: "#8a97a6", fontSize: 11, fontFamily: "var(--mono)" }}
              label={{ value: "Time (min)", fill: "#4a5765", fontSize: 11, position: "insideBottom", offset: -4 }}
            />
            <YAxis
              stroke="#4a5765"
              tick={{ fill: "#8a97a6", fontSize: 11, fontFamily: "var(--mono)" }}
              label={{ value: "Altitude (km)", angle: -90, fill: "#4a5765", fontSize: 11, position: "insideLeft" }}
            />
            <Tooltip
              contentStyle={{
                background: "#0b1017", border: "1px solid #1b2632", borderRadius: 4,
                fontFamily: "var(--mono)", fontSize: 12,
              }}
              labelStyle={{ color: "#8a97a6" }}
            />
            <Line type="monotone" dataKey="alt" stroke="#00e5c7" strokeWidth={2} dot={false} isAnimationActive={false} />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </>
  );
}
