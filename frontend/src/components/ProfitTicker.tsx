import { TrendingDown, TrendingUp } from "lucide-react";

type Props = {
  recovered: number;
  lost: number;
};

export function ProfitTicker({ recovered, lost }: Props) {
  const fmt = (n: number) =>
    n.toLocaleString(undefined, { style: "currency", currency: "USD", maximumFractionDigits: 0 });
  return (
    <div className="flex items-stretch gap-0 border-b border-slate-200 bg-slate-50 overflow-hidden">
      <div className="flex shrink-0 items-center gap-2 px-4 py-2 bg-corp-navy text-white text-xs font-semibold uppercase tracking-wider">
        Intelligence Sync
      </div>
      <div className="flex flex-1 min-w-0 items-center gap-8 py-2 px-4 whitespace-nowrap overflow-x-auto">
        <span className="inline-flex items-center gap-2 text-sm text-slate-800">
          <TrendingUp className="w-4 h-4 text-emerald-600 shrink-0" aria-hidden />
          <span className="font-medium text-slate-600">Total recovered value</span>
          <span className="font-mono font-semibold text-emerald-700">{fmt(recovered)}</span>
        </span>
        <span className="inline-flex items-center gap-2 text-sm text-slate-800">
          <TrendingDown className="w-4 h-4 text-red-600 shrink-0" aria-hidden />
          <span className="font-medium text-slate-600">Total lost value</span>
          <span className="font-mono font-semibold text-red-700">{fmt(lost)}</span>
        </span>
        <span className="text-xs text-slate-500">
          NRV engine and disposition classifier drive recovery estimates from synthetic WSI returns.
        </span>
      </div>
    </div>
  );
}
