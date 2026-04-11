import { Activity, MapPin } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import type { NetworkMapResponse } from "../api";
import { fetchNetworkMap } from "../api";

export function NetworkPage({ stressWms }: { stressWms: boolean }) {
  const [data, setData] = useState<NetworkMapResponse | null>(null);
  const [err, setErr] = useState<string | null>(null);

  const load = useCallback(async () => {
    setErr(null);
    try {
      setData(await fetchNetworkMap(stressWms));
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Failed");
    }
  }, [stressWms]);

  useEffect(() => {
    load();
  }, [load]);

  return (
    <div className="flex flex-1 flex-col gap-4 p-6 overflow-auto">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="font-display text-2xl font-semibold text-corp-navy">Network Map</h1>
          <p className="mt-1 text-sm text-slate-600">
            Hub capacity, routed SKU flows, and congestion-aware paths. Use the header control to spike capacity to 99%.
          </p>
        </div>
      </div>

      {err && <div className="rounded-md border border-red-200 bg-red-50 px-4 py-2 text-sm text-red-800">{err}</div>}

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <div className="lg:col-span-1 space-y-3">
          <h2 className="text-xs font-bold uppercase tracking-wider text-slate-500">Fulfillment hubs</h2>
          {(data?.nodes ?? []).map((n) => (
            <div
              key={n.id}
              className={`flex items-start gap-3 rounded-lg border p-3 ${
                n.capacity_pct >= 90 ? "border-red-200 bg-red-50" : n.capacity_pct >= 75 ? "border-amber-200 bg-amber-50" : "border-slate-200 bg-white"
              }`}
            >
              <MapPin className="mt-0.5 h-4 w-4 text-slate-500 shrink-0" aria-hidden />
              <div className="min-w-0">
                <div className="font-semibold text-sm text-corp-navy">{n.label}</div>
                <div className="text-xs text-slate-500 font-mono">{n.id}</div>
                <div className="mt-1 flex items-center gap-2 text-xs">
                  <Activity className="h-3.5 w-3.5" aria-hidden />
                  <span>Capacity {n.capacity_pct}%</span>
                </div>
              </div>
            </div>
          ))}
        </div>

        <div className="lg:col-span-2 rounded-lg border border-slate-200 bg-slate-50 p-4 min-h-[320px]">
          <h2 className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-3">Route edges (origin to hub)</h2>
          <div className="grid gap-2 max-h-[480px] overflow-auto">
            {(data?.edges ?? []).map((e, i) => (
              <div key={i} className="flex flex-wrap items-center gap-2 rounded border border-slate-200 bg-white px-3 py-2 text-xs">
                <span className="font-mono font-semibold text-corp-navy">{e.sku_id}</span>
                <span className="text-slate-400">to</span>
                <span className="font-medium">{e.hub}</span>
                {e.action && <span className="rounded bg-slate-100 px-2 py-0.5 text-[10px] uppercase">{e.action}</span>}
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
