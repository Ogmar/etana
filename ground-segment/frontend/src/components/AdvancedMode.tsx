import { LiveState } from "../lib/useLiveTelemetry";
import { TheoreticalParam } from "../lib/theoreticalModel";
import { TheoryChart } from "./TheoryChart";
import { TimeSeriesChart } from "./TimeSeriesChart";

interface AdvancedModeProps {
  series: LiveState["series"];
}

const THEORY_PARAMS: TheoreticalParam[] = ["ozone_raw", "co2_raw", "temp_internal", "temp_external"];

export function AdvancedMode({ series }: AdvancedModeProps) {
  const altSeries = series["gps_altitude"] ?? [];

  return (
    <>
      <div className="stage-head">
        <h1>Telemetry · Advanced</h1>
        <p>actual vs theoretical · all metrics</p>
      </div>
      <div className="advgrid">
        <TimeSeriesChart
          label="Altitude"
          unit="km"
          data={altSeries.map((p) => ({ t: p.t, v: p.v / 1000 }))}
        />
        {THEORY_PARAMS.map((key) => (
          <TheoryChart key={key} paramKey={key} paramSeries={series[key] ?? []} altSeries={altSeries} />
        ))}
        <TimeSeriesChart label="Battery" unit="V" data={series["battery"] ?? []} />
        <TimeSeriesChart label="Satellites" data={series["gps_sats"] ?? []} curveType="stepAfter" />
        <TimeSeriesChart label="Latitude" unit="°" data={series["gps_latitude"] ?? []} />
        <TimeSeriesChart label="Longitude" unit="°" data={series["gps_longitude"] ?? []} />
      </div>
    </>
  );
}
