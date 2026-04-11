import { Canvas } from "@react-three/fiber";
import { OrbitControls, PerspectiveCamera } from "@react-three/drei";
import type { HeatPoint } from "../api";

function TableRig() {
  return (
    <group>
      <mesh position={[0.5, 0.36, 0.5]} castShadow receiveShadow>
        <boxGeometry args={[0.9, 0.04, 0.6]} />
        <meshStandardMaterial color="#e8dfd0" metalness={0.05} roughness={0.6} />
      </mesh>
      {[
        [0.15, 0.18, 0.15],
        [0.85, 0.18, 0.15],
        [0.15, 0.18, 0.85],
        [0.85, 0.18, 0.85],
      ].map((p, i) => (
        <mesh key={i} position={p as [number, number, number]} castShadow>
          <cylinderGeometry args={[0.03, 0.04, 0.36, 12]} />
          <meshStandardMaterial color="#94a3b8" metalness={0.2} roughness={0.5} />
        </mesh>
      ))}
    </group>
  );
}

function HotSpheres({ points }: { points: HeatPoint[] }) {
  return (
    <>
      {points.map((pt, i) => {
        const [x, y, z] = pt.position;
        const r = 0.06 + pt.intensity * 0.05;
        return (
          <mesh key={i} position={[x, y, z]} castShadow>
            <sphereGeometry args={[r, 24, 24]} />
            <meshStandardMaterial
              color={pt.intensity > 0.7 ? "#dc2626" : "#ea580c"}
              emissive={pt.intensity > 0.7 ? "#7f1d1d" : "#9a3412"}
              emissiveIntensity={0.35}
              metalness={0.1}
              roughness={0.4}
            />
          </mesh>
        );
      })}
    </>
  );
}

export function RiskHeatmap3D({ heatmap }: { heatmap: HeatPoint[] }) {
  const pts = heatmap?.length ? heatmap : [{ component: "baseline", intensity: 0.35, position: [0.5, 0.42, 0.5] }];
  return (
    <div className="h-[340px] w-full rounded-lg border border-slate-200 bg-slate-50 overflow-hidden">
      <Canvas shadows dpr={[1, 2]}>
        <PerspectiveCamera makeDefault position={[1.2, 0.85, 1.2]} fov={45} />
        <ambientLight intensity={0.65} />
        <directionalLight position={[3, 5, 2]} intensity={1.1} castShadow shadow-mapSize-width={1024} shadow-mapSize-height={1024} />
        <TableRig />
        <HotSpheres points={pts} />
        <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0.5, 0, 0.5]} receiveShadow>
          <planeGeometry args={[3, 3]} />
          <meshStandardMaterial color="#f1f5f9" />
        </mesh>
        <OrbitControls enablePan target={[0.5, 0.35, 0.5]} minDistance={0.8} maxDistance={3} />
      </Canvas>
      <p className="px-3 py-1 text-[10px] text-slate-500 border-t border-slate-200 bg-white">
        Risk heatmap overlays failure-prone regions on a generic furniture rig (unit cube space).
      </p>
    </div>
  );
}
