// Ground-truth generative sensor model, ported from
// services/simulator/simulator/telemetry.py — keep in sync if that changes.
// These are the altitude-dependent functions the simulator uses to synthesize
// ozone/CO2/temperature, so plotting them against decoded samples validates
// the decode + calibration pipeline end to end.

export function airTempC(altM: number): number {
  if (altM < 11000) return 15.0 - 6.5 * (altM / 1000.0);
  if (altM < 20000) return -56.5;
  return -56.5 + 1.0 * ((altM - 20000) / 1000.0);
}

export function internalTempC(altM: number): number {
  return airTempC(altM) + 20.0;
}

export function ozonePpb(altM: number): number {
  const peakAlt = 25000.0;
  const peakPpb = 180.0;
  const width = 8000.0;
  const groundPpb = 30.0;
  return groundPpb + peakPpb * Math.exp(-((altM - peakAlt) ** 2) / (2 * width ** 2));
}

export function co2Ppm(altM: number): number {
  return 420.0 - 10.0 * (altM / 30000.0);
}

export type TheoreticalParam = "ozone_raw" | "co2_raw" | "temp_internal" | "temp_external";

export const THEORETICAL_MODELS: Record<TheoreticalParam, (altM: number) => number> = {
  ozone_raw: ozonePpb,
  co2_raw: co2Ppm,
  temp_internal: internalTempC,
  temp_external: airTempC,
};

export const THEORETICAL_UNITS: Record<TheoreticalParam, string> = {
  ozone_raw: "ppb",
  co2_raw: "ppm",
  temp_internal: "°C",
  temp_external: "°C",
};

export const THEORETICAL_LABELS: Record<TheoreticalParam, string> = {
  ozone_raw: "Ozone",
  co2_raw: "CO₂",
  temp_internal: "Temp (int)",
  temp_external: "Temp (ext)",
};
