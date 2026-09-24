import { MISSION_TIMELINE } from "../data/missionTimeline";
import { TimelineEntry } from "./TimelineEntry";

export function MissionTimeline() {
  return (
    <div className="timeline">
      {MISSION_TIMELINE.map((entry, i) => (
        <TimelineEntry key={entry.id} entry={entry} side={i % 2 === 0 ? "left" : "right"} />
      ))}
    </div>
  );
}
