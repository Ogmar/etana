// Mission story timeline. Content is drafted from the project's own docs
// (docs/SPECIFICATION.md, docs/DESIGN.md) rather than invented — same
// "cite the real source" approach used for the vehicle page's part specs.
// No real mission photos exist yet (pre-flight project); each entry gets an
// inline icon. `image` is left as an optional future field so a real photo
// can replace the icon later without a code change.

export type TimelineIconKey = "mission" | "codec" | "transport" | "archive" | "dashboard" | "future";

export interface TimelineLink {
  to: string;
  label: string;
}

export interface TimelineEntryData {
  id: string;
  phase: string;
  title: string;
  text: string;
  icon: TimelineIconKey;
  image?: string;
  link?: TimelineLink;
}

export const MISSION_TIMELINE: TimelineEntryData[] = [
  {
    id: "mission",
    phase: "Etana",
    title: "The mission",
    text: "Etana is a high-altitude balloon mission. The vehicle, Eagle-1, carries an atmospheric payload to approximately 30km, measuring ozone and CO₂ concentration against altitude while reporting position for tracking and recovery.",
    icon: "mission",
  },
  {
    id: "phase0",
    phase: "Phase 0 · Complete",
    title: "Speaking one language",
    text: "A single mission database defines the telemetry packet structure once. Both the flight software's encoder and the ground segment's decoder read the same file, so there is exactly one definition of what a byte means — never two implementations to keep in sync.",
    icon: "codec",
  },
  {
    id: "phase1",
    phase: "Phase 1 · Complete",
    title: "A transport that doesn't care",
    text: "The receive path talks to a packet-source interface, not a radio. During development, a simulator flies a full ascent-burst-descent profile over TCP through that same seam — so the ground segment is built and tested before flight hardware exists.",
    icon: "transport",
    link: { to: "/vehicle", label: "See the vehicle we're building" },
  },
  {
    id: "phase2",
    phase: "Phase 2 · Complete",
    title: "Nothing gets lost",
    text: "Every received packet is archived bit-exact before decoding. Decoded parameter values are a separate, derived store — regenerable by re-decoding the raw archive, so a revised calibration curve can be applied after the fact without re-flying.",
    icon: "archive",
  },
  {
    id: "phase3",
    phase: "Phase 3 · Complete",
    title: "Watching it fly",
    text: "A Django API reads the archive; a React dashboard polls it live — flight profile, position, payload readings, packet loss, and an actual-vs-theoretical comparison for every altitude-dependent sensor.",
    icon: "dashboard",
    link: { to: "/dashboard", label: "Open the live dashboard" },
  },
  {
    id: "phase4",
    phase: "Phase 4+ · Planned",
    title: "What's next",
    text: "A landing predictor integrating forward trajectory through wind data, cutdown commanding, a replay UI for recovered onboard storage — and the first flight itself.",
    icon: "future",
    link: { to: "/vehicle", label: "See the hardware that will carry it up" },
  },
];
