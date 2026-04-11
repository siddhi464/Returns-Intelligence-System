import { useEffect, useState } from "react";
import type { GoldenRecord } from "../api";
import { fetchDisposition } from "../api";
import { RiskHeatmap3D } from "../components/RiskHeatmap3D";

export function TwinPage({ stressWms }: { stressWms: boolean }) {
  const [records, setRecords] = useState<GoldenRecord[]>([]);
  const [sel, setSel] = useState<string>("");

  useEffect(() => {
    let cancel = false;
    fetchDisposition(stressWms)
      .then((d) => {
        if (cancel) return;
        setRecords(d.records);
        setSel((prev) => {
          if (prev && d.records.some((r) => r.sku_id === prev)) return prev;
          return d.records[0]?.sku_id ?? "";
        });
      })
      .catch(() => {});
    return () => {
      cancel = true;
    };
  }, [stressWms]);

  const r = records.find((x) => x.sku_id === sel) ?? records[0];

  return (
    <div className="flex flex-1 flex-col gap-4 p-6 overflow-auto">
      <div>
        <h1 className="font-display text-2xl font-semibold text-corp-navy">Durability Digital Twin</h1>
        <p className="mt-1 text-sm text-slate-600">
          Health index, failure components, and 3D risk heatmap coordinates for field and QA review.
        </p>
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-4">
        <div className="lg:col-span-1 rounded-lg border border-slate-200 bg-white p-3">
          <label className="text-[10px] font-bold uppercase text-slate-500">SKU</label>
          <select
            className="mt-1 w-full rounded border border-slate-200 px-2 py-2 text-sm"
            value={r?.sku_id ?? ""}
            onChange={(e) => setSel(e.target.value)}
          >
            {records.map((x) => (
              <option key={x.sku_id} value={x.sku_id}>
                {x.sku_id}
              </option>
            ))}
          </select>
          {r && (
            <dl className="mt-4 space-y-2 text-xs">
              <div>
                <dt className="text-slate-500">Health index</dt>
                <dd className="font-mono text-lg font-semibold text-corp-navy">{r.health_index}</dd>
              </div>
              <div>
                <dt className="text-slate-500">Top failure component</dt>
                <dd className="font-medium">{r.digital_twin.top_failure_component}</dd>
              </div>
              <div>
                <dt className="text-slate-500">Entities</dt>
                <dd>{r.digital_twin.physical_entities.join(", ") || "—"}</dd>
              </div>
              <div>
                <dt className="text-slate-500">Failure modes</dt>
                <dd>{r.digital_twin.failure_modes.join(", ") || "—"}</dd>
              </div>
            </dl>
          )}
        </div>
        <div className="lg:col-span-3">{r && <RiskHeatmap3D heatmap={r.digital_twin.heatmap_coordinates} />}</div>
      </div>
    </div>
  );
}
