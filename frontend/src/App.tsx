import { Route, Routes } from "react-router-dom";
import { useState } from "react";
import { Zap } from "lucide-react";
import { Sidebar } from "./components/Sidebar";
import { DispositionPage } from "./pages/DispositionPage";
import { NetworkPage } from "./pages/NetworkPage";
import { TwinPage } from "./pages/TwinPage";

export default function App() {
  const [stressWms, setStressWms] = useState(false);

  return (
    <div className="min-h-screen bg-white text-slate-900">
      <header className="fixed top-0 left-0 right-0 z-50 flex h-14 items-center justify-between border-b border-slate-200 bg-white pl-56 pr-6">
        <div className="flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-md bg-corp-navy text-amber-200 text-xs font-bold">WSI</div>
          <div>
            <div className="text-sm font-semibold text-corp-navy">Sentinel SCM Intelligence</div>
            <div className="text-[10px] uppercase tracking-widest text-slate-400">Williams Sonoma Inc.</div>
          </div>
        </div>
        <button
          type="button"
          onClick={() => setStressWms((s) => !s)}
          className={`inline-flex items-center gap-2 rounded-md px-3 py-1.5 text-xs font-semibold ${
            stressWms ? "bg-amber-600 text-white" : "border border-slate-200 bg-white text-corp-navy hover:bg-slate-50"
          }`}
        >
          <Zap className="h-3.5 w-3.5" aria-hidden />
          Stress test {stressWms ? "ON" : "OFF"}
        </button>
      </header>
      <Sidebar />
      <main className="pl-56 pt-14 min-h-screen flex flex-col bg-slate-50/80">
        <Routes>
          <Route path="/" element={<DispositionPage stressWms={stressWms} />} />
          <Route path="/network" element={<NetworkPage stressWms={stressWms} />} />
          <Route path="/twin" element={<TwinPage stressWms={stressWms} />} />
        </Routes>
      </main>
    </div>
  );
}
