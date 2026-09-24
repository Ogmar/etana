// Placeholder Eagle-1 part catalog. No real CAD model exists yet, so each
// part is a primitive shape positioned to read as a generic HAB flight
// train. Specs/reasons are generic where no design doc exists yet, and cite
// the real documented decisions where they do:
//   - flight-software/docs/mcu-lora-selection.md (MCU + LoRa module)
//   - docs/SPECIFICATION.md (mission scope, telemetry APIDs, LoRa band)
//
// Materials are tuned PBR properties (no texture images available yet) —
// roughness/metalness/transmission approximate latex, fabric, composite and
// bare metal so the model reads as more than flat placeholder color blocks.

export type PartGeometry =
  | { type: "sphere"; radius: number }
  | { type: "cylinder"; radiusTop: number; radiusBottom: number; height: number }
  | { type: "box"; width: number; height: number; depth: number }
  | { type: "cone"; radius: number; height: number };

export interface PartMaterial {
  color: string;
  roughness: number;
  metalness: number;
  transmission?: number;
  clearcoat?: number;
}

export interface VehiclePart {
  id: string;
  label: string;
  spec: string;
  reason: string;
  geometry: PartGeometry;
  position: [number, number, number];
  rotation?: [number, number, number];
  material: PartMaterial;
  // World-space offset (from `position`) where the callout bubble anchors.
  labelOffset: [number, number, number];
}

export const VEHICLE_PARTS: VehiclePart[] = [
  {
    id: "envelope",
    label: "Balloon envelope",
    spec: "Latex sounding balloon, generic HAB sizing (~1600g class)",
    reason: "Standard, cheap, well-characterized burst behavior for a first flight.",
    geometry: { type: "sphere", radius: 1.6 },
    position: [0, 5.2, 0],
    material: { color: "#eef2f4", roughness: 0.3, metalness: 0, transmission: 0.35, clearcoat: 0.4 },
    labelOffset: [2.2, 0.6, 0],
  },
  {
    id: "flight_train",
    label: "Flight train",
    spec: "Paracord rigging with swivel: balloon → parachute → payload",
    reason: "Standard low-risk rigging; the swivel prevents the payload from spinning up on descent.",
    geometry: { type: "cylinder", radiusTop: 0.03, radiusBottom: 0.03, height: 2.6 },
    position: [0, 3.3, 0],
    material: { color: "#2a2f36", roughness: 0.9, metalness: 0 },
    labelOffset: [1.8, 0, 0],
  },
  {
    id: "parachute",
    label: "Recovery parachute",
    spec: "Sized for a ~5-6 m/s descent rate at landing",
    reason: "Mechanical, uplink-independent recovery — matches the mission's downlink-only scope (SPECIFICATION.md §2).",
    geometry: { type: "cone", radius: 0.7, height: 0.9 },
    position: [0, 1.9, 0],
    rotation: [Math.PI, 0, 0],
    material: { color: "#ff6a13", roughness: 0.75, metalness: 0 },
    labelOffset: [2.0, 0.3, 0],
  },
  {
    id: "payload_box",
    label: "Avionics enclosure",
    spec: "STM32L4 MCU (Cortex-M4, 80-120MHz, -40..85°C) + SX1276/7/8/9 LoRa (902-928MHz ISM)",
    reason: "Real trade study: STM32L4 met all requirements at the lowest cost per unit; SX1276/7/8/9 chosen over the cheaper RFM95W because its -20°C floor doesn't cover the mission's -55°C requirement (mcu-lora-selection.md).",
    geometry: { type: "box", width: 1.1, height: 0.7, depth: 0.9 },
    position: [0, 1.0, 0],
    material: { color: "#3a3f47", roughness: 0.45, metalness: 0.15 },
    labelOffset: [2.1, -0.4, 0],
  },
  {
    id: "antenna",
    label: "LoRa antenna",
    spec: "Wire monopole, 902-928MHz ISM band",
    reason: "Matches the mission's LoRa downlink band (SPECIFICATION.md §5).",
    geometry: { type: "cylinder", radiusTop: 0.02, radiusBottom: 0.02, height: 0.9 },
    position: [0.55, 1.45, 0.3],
    rotation: [0, 0, -0.35],
    material: { color: "#c7ccd1", roughness: 0.3, metalness: 0.85 },
    labelOffset: [1.6, 0.9, 0],
  },
  {
    id: "sensor_boom",
    label: "Sensor boom",
    spec: "External ozone/CO₂ sensor package, APID 200 @ 0.2Hz",
    reason: "Mounted outside the enclosure for true ambient readings — mirrors the mission DB's own temp_external vs temp_internal distinction.",
    geometry: { type: "cylinder", radiusTop: 0.04, radiusBottom: 0.04, height: 0.8 },
    position: [-0.75, 1.0, 0],
    rotation: [0, 0, Math.PI / 2],
    material: { color: "#c7ccd1", roughness: 0.4, metalness: 0.6 },
    labelOffset: [-2.1, -0.4, 0],
  },
];
