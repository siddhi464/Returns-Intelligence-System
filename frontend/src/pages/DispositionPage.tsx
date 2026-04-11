import { RefreshCw } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import type { DispositionResponse, GoldenRecord } from "../api";
import { fetchDisposition } from "../api";
import { ProfitTicker } from "../components/ProfitTicker";

function actionBadge(action: string) {
  const a = action.toUpperCase();
  if (a.includes("RETURNLESS")) return "bg-red-100 text-red-800";
  if (a.includes("RESTOCK")) return "bg-emerald-100 text-emerald-800";
  if (a.includes("REFURB")) return "bg-amber-100 text-amber-900";
  return "bg-slate-100 text-slate-800";
}

export function DispositionPage({ stressWms }: { stressWms: boolean }) {
  const [data, setData] = useState<DispositionResponse | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    setErr(null);
    try {
      const d = await fetchDisposition(stressWms);
      setData(d);
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Load failed");
    } finally {
      setLoading(false);
    }
  }, [stressWms]);

  useEffect(() => {
    load();
  }, [load]);

  const rows: GoldenRecord[] = data?.records ?? [];

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      {data && <ProfitTicker recovered={data.profit_recovery.total_recovered_value} lost={data.profit_recovery.total_lost_value} />}
      <div className="flex flex-1 flex-col gap-4 p-6 overflow-auto">
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div>
            <h1 className="font-display text-2xl font-semibold text-corp-navy">Disposition Overview</h1>
            <p className="mt-1 text-sm text-slate-600">
              Golden record per SKU: NRV, AI condition grade, routing, and durability signals.
            </p>
          </div>
          <button
            type="button"
            onClick={() => load()}
            className="inline-flex items-center gap-2 rounded-md border border-slate-200 bg-white px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
          >
            <RefreshCw className="h-4 w-4" aria-hidden />
            Refresh
          </button>
        </div>

        {stressWms && (
          <div className="rounded-md border border-amber-300 bg-amber-50 px-4 py-2 text-sm text-amber-900">
            Stress test active: WMS capacities simulated at 99%. Routing re-optimized for congestion.
          </div>
        )}

        {err && <div className="rounded-md border border-red-200 bg-red-50 px-4 py-2 text-sm text-red-800">{err}</div>}

        <div className="rounded-lg border border-slate-200 bg-white shadow-sm overflow-auto">
          <table className="table-dense table-fixed w-full">
            <colgroup>
              <col className="w-[10%]" />
              <col className="w-[8%]" />
              <col className="w-[7%]" />
              <col className="w-[8%]" />
              <col className="w-[10%]" />
              <col className="w-[12%]" />
              <col className="w-[10%]" />
              <col className="w-[8%]" />
              <col className="w-[27%]" />
            </colgroup>
            <thead>
              <tr>
                <th>SKU</th>
                <th>Product</th>
                <th>Health</th>
                <th>NRV</th>
                <th>NRV % MSRP</th>
                <th>Action</th>
                <th>Condition</th>
                <th>Sentiment</th>
                <th>Hub / Summary</th>
              </tr>
            </thead>
            <tbody>
              {loading && (
                <tr>
                  <td colSpan={9} className="py-12 text-center text-slate-500">
                    Loading disposition insights…
                  </td>
                </tr>
              )}
              {!loading &&
                rows.map((r) => (
                  <tr key={r.sku_id} className="hover:bg-slate-50">
                    <td className="font-mono text-[11px]">{r.sku_id}</td>
                    <td className="truncate max-w-[1px]" title={r.name}>
                      {r.name}
                    </td>
                    <td className="font-mono">{r.health_index}</td>
                    <td className="font-mono">${r.nrv_value.toFixed(0)}</td>
                    <td className="font-mono">{r.nrv_pct_msrp}%</td>
                    <td>
                      <span className={`inline-block rounded px-2 py-0.5 text-[10px] font-semibold ${actionBadge(r.recommended_action)}`}>
                        {r.recommended_action}
                      </span>
                    </td>
                    <td>{r.condition_grade}</td>
                    <td className="font-mono">{r.sentiment_score.toFixed(2)}</td>
                    <td className="text-[11px] text-slate-600">
                      <div className="font-medium text-slate-800">{r.routing.target_hub}</div>
                      <div className="truncate" title={r.ai_summary}>
                        {r.ai_summary}
                      </div>
                      <div className="text-slate-400">
                        Cap {r.routing.capacity_status}
                        {r.routing.savings_via_clustering > 0
                          ? ` · Cluster save $${r.routing.savings_via_clustering.toFixed(0)}`
                          : ""}
                      </div>
                    </td>
                  </tr>
                ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
