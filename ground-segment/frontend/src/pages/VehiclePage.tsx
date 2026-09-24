import { useState } from "react";
import { VehicleScene3D } from "../components/VehicleScene3D";
import { VEHICLE_PARTS } from "../data/vehicleParts";

export default function VehiclePage() {
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [hoveredId, setHoveredId] = useState<string | null>(null);

  return (
    <div className="console">
      <div className="stage vehiclestage vehiclestage-full">
        <div className="stage-head">
          <h1>Eagle-1 · Vehicle</h1>
          <p>drag to rotate · click a part to inspect it</p>
        </div>
        <div className="vehiclecanvas">
          <VehicleScene3D
            parts={VEHICLE_PARTS}
            selectedId={selectedId}
            hoveredId={hoveredId}
            onSelect={setSelectedId}
            onHover={setHoveredId}
          />
        </div>
      </div>
    </div>
  );
}
