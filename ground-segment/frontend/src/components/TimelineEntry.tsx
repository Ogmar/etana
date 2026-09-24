import { motion } from "framer-motion";
import { Link } from "react-router-dom";
import { TimelineEntryData } from "../data/missionTimeline";
import { TimelineIcon } from "./TimelineIcons";

interface TimelineEntryProps {
  entry: TimelineEntryData;
  side: "left" | "right";
}

export function TimelineEntry({ entry, side }: TimelineEntryProps) {
  return (
    <div className={`timeline-entry ${side}`}>
      <div className="timeline-icon">
        <TimelineIcon icon={entry.icon} />
      </div>
      <motion.div
        className="timeline-content"
        initial={{ opacity: 0, x: side === "left" ? -40 : 40 }}
        whileInView={{ opacity: 1, x: 0 }}
        viewport={{ once: true, margin: "-80px" }}
        transition={{ duration: 0.6, ease: "easeOut" }}
      >
        <span className="timeline-phase">{entry.phase}</span>
        <h3>{entry.title}</h3>
        <p>{entry.text}</p>
        {entry.link && (
          <Link className="timeline-link" to={entry.link.to}>
            {entry.link.label} →
          </Link>
        )}
      </motion.div>
    </div>
  );
}
