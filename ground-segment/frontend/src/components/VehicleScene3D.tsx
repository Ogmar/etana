import { useMemo } from "react";
import { Canvas } from "@react-three/fiber";
import { Html, OrbitControls, Stars } from "@react-three/drei";
import { theme } from "../lib/theme";
import { VehiclePart } from "../data/vehicleParts";

interface VehicleScene3DProps {
  parts: VehiclePart[];
  selectedId: string | null;
  hoveredId: string | null;
  onSelect: (id: string | null) => void;
  onHover: (id: string | null) => void;
}

export function VehicleScene3D({ parts, selectedId, hoveredId, onSelect, onHover }: VehicleScene3DProps) {
  const selected = parts.find((p) => p.id === selectedId) ?? null;

  return (
    <Canvas
      camera={{ fov: 40, position: [7, 6, 8] }}
      dpr={[1, 1.5]}
      onPointerMissed={() => onSelect(null)}
    >
      <color attach="background" args={[theme.bg]} />
      <Stars radius={50} depth={30} count={2500} factor={2} saturation={0} fade speed={0.3} />

      <ambientLight intensity={0.35} />
      <directionalLight position={[4, 6, 4]} intensity={1.4} />
      <directionalLight position={[-5, -1, -4]} intensity={0.18} color={theme.blue} />

      {parts.map((part) => (
        <PartMesh
          key={part.id}
          part={part}
          isSelected={selectedId === part.id}
          isHovered={hoveredId === part.id}
          dim={selectedId != null && selectedId !== part.id}
          onSelect={onSelect}
          onHover={onHover}
        />
      ))}

      {selected && (
        <Html position={selected.labelOffset.map((v, i) => v + selected.position[i]) as [number, number, number]} occlude>
          <div className="partbubble">
            <button className="partbubble-close" onClick={() => onSelect(null)} aria-label="Close">
              ×
            </button>
            <h3>{selected.label}</h3>
            <p className="partbubble-spec">{selected.spec}</p>
            <p className="partbubble-reason">{selected.reason}</p>
          </div>
        </Html>
      )}

      <OrbitControls
        target={[0, 3.7, 0]}
        enableDamping
        dampingFactor={0.08}
        minDistance={4}
        maxDistance={24}
      />
    </Canvas>
  );
}

function PartMesh({
  part, isSelected, isHovered, dim, onSelect, onHover,
}: {
  part: VehiclePart;
  isSelected: boolean;
  isHovered: boolean;
  dim: boolean;
  onSelect: (id: string) => void;
  onHover: (id: string | null) => void;
}) {
  const emissiveIntensity = isSelected ? 0.7 : isHovered ? 0.35 : 0;
  const opacity = dim && !isSelected ? 0.35 : 1;
  const m = part.material;

  const geometryEl = useMemo(() => {
    const g = part.geometry;
    switch (g.type) {
      case "sphere":
        return <sphereGeometry args={[g.radius, 32, 24]} />;
      case "cylinder":
        return <cylinderGeometry args={[g.radiusTop, g.radiusBottom, g.height, 24]} />;
      case "box":
        return <boxGeometry args={[g.width, g.height, g.depth]} />;
      case "cone":
        return <coneGeometry args={[g.radius, g.height, 24]} />;
      default:
        return null;
    }
  }, [part.geometry]);

  return (
    <mesh
      position={part.position}
      rotation={part.rotation}
      onClick={(e) => {
        e.stopPropagation();
        onSelect(part.id);
      }}
      onPointerOver={(e) => {
        e.stopPropagation();
        onHover(part.id);
        document.body.style.cursor = "pointer";
      }}
      onPointerOut={() => {
        onHover(null);
        document.body.style.cursor = "auto";
      }}
    >
      {geometryEl}
      <meshPhysicalMaterial
        color={m.color}
        roughness={m.roughness}
        metalness={m.metalness}
        transmission={m.transmission ?? 0}
        clearcoat={m.clearcoat ?? 0}
        thickness={m.transmission ? 0.6 : undefined}
        emissive={theme.cyan}
        emissiveIntensity={emissiveIntensity}
        transparent
        opacity={opacity}
      />
    </mesh>
  );
}
