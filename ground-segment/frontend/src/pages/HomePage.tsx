import { motion } from "framer-motion";
import { Link } from "react-router-dom";
import { MissionTimeline } from "../components/MissionTimeline";

export default function HomePage() {
  return (
    <div className="home">
      <motion.div
        className="hero"
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.8, ease: "easeOut" }}
      >
        <h1>ETANA</h1>
        <p>
          A high-altitude balloon mission. Eagle-1 carries an atmospheric payload
          to ~30km, measuring ozone and CO₂ against altitude while reporting
          position for tracking and recovery.
        </p>
      </motion.div>

      <MissionTimeline />

      <motion.div
        className="closing-cta"
        initial={{ opacity: 0, y: 30 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true, margin: "-80px" }}
        transition={{ duration: 0.6, ease: "easeOut" }}
      >
        <Link className="closing-cta-card" to="/vehicle">
          <h3>Explore the vehicle</h3>
          <p>A 3D look at Eagle-1's parts, and why each one is built the way it is.</p>
        </Link>
        <Link className="closing-cta-card" to="/dashboard">
          <h3>Open the dashboard</h3>
          <p>Live telemetry, flight history, and theoretical-vs-actual comparisons.</p>
        </Link>
      </motion.div>
    </div>
  );
}
