import { TimelineIconKey } from "../data/missionTimeline";

// Minimal single-color line-art icons, one per timeline phase. Stroke is
// `currentColor` so callers set color via CSS. No image assets exist for
// this pre-flight project, so these stand in until real photos do.

const common = {
  width: 28,
  height: 28,
  viewBox: "0 0 32 32",
  fill: "none",
  stroke: "currentColor",
  strokeWidth: 1.6,
  strokeLinecap: "round" as const,
  strokeLinejoin: "round" as const,
};

function MissionIcon() {
  return (
    <svg {...common}>
      <circle cx="16" cy="12" r="8" />
      <path d="M16 20v8" />
      <path d="M12 26h8" />
    </svg>
  );
}

function CodecIcon() {
  return (
    <svg {...common}>
      <rect x="6" y="8" width="20" height="16" rx="2" />
      <path d="M16 8v16" strokeDasharray="2 3" />
      <circle cx="16" cy="16" r="1.6" fill="currentColor" stroke="none" />
    </svg>
  );
}

function TransportIcon() {
  return (
    <svg {...common}>
      <path d="M16 26V14" />
      <path d="M11 19c1.4-1.4 3.2-2 5-2s3.6.6 5 2" />
      <path d="M7.5 14.5c2.3-2.3 5.4-3.5 8.5-3.5s6.2 1.2 8.5 3.5" />
      <circle cx="16" cy="26" r="1.6" fill="currentColor" stroke="none" />
    </svg>
  );
}

function ArchiveIcon() {
  return (
    <svg {...common}>
      <ellipse cx="16" cy="9" rx="9" ry="3.5" />
      <path d="M7 9v14c0 1.9 4 3.5 9 3.5s9-1.6 9-3.5V9" />
      <path d="M7 16c0 1.9 4 3.5 9 3.5s9-1.6 9-3.5" />
    </svg>
  );
}

function DashboardIcon() {
  return (
    <svg {...common}>
      <rect x="5" y="7" width="22" height="15" rx="2" />
      <path d="M9 18l4-5 3 3 5-7" />
      <path d="M12 27h8" />
      <path d="M16 22v5" />
    </svg>
  );
}

function FutureIcon() {
  return (
    <svg {...common}>
      <path d="M16 26V9" strokeDasharray="3 3" />
      <path d="M11 13l5-5 5 5" />
    </svg>
  );
}

const ICONS: Record<TimelineIconKey, () => JSX.Element> = {
  mission: MissionIcon,
  codec: CodecIcon,
  transport: TransportIcon,
  archive: ArchiveIcon,
  dashboard: DashboardIcon,
  future: FutureIcon,
};

export function TimelineIcon({ icon }: { icon: TimelineIconKey }) {
  const Cmp = ICONS[icon];
  return <Cmp />;
}
