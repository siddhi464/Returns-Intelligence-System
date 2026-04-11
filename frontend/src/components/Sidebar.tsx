import { Boxes, LayoutDashboard, Network } from "lucide-react";
import { NavLink } from "react-router-dom";

const linkCls = ({ isActive }: { isActive: boolean }) =>
  `flex items-center gap-3 px-4 py-2.5 text-sm font-medium border-l-4 transition-colors ${
    isActive
      ? "border-corp-gold bg-amber-50 text-corp-navy"
      : "border-transparent text-slate-600 hover:bg-slate-50 hover:text-corp-navy"
  }`;

export function Sidebar() {
  return (
    <aside className="fixed left-0 top-0 z-40 flex h-screen w-56 flex-col border-r border-slate-200 bg-white pt-14">
      <div className="px-4 py-3 text-[10px] font-semibold uppercase tracking-widest text-slate-400">Navigation</div>
      <nav className="flex flex-col gap-0.5">
        <NavLink to="/" end className={linkCls}>
          <LayoutDashboard className="w-4 h-4 shrink-0" aria-hidden />
          Disposition Overview
        </NavLink>
        <NavLink to="/network" className={linkCls}>
          <Network className="w-4 h-4 shrink-0" aria-hidden />
          Network Map
        </NavLink>
        <NavLink to="/twin" className={linkCls}>
          <Boxes className="w-4 h-4 shrink-0" aria-hidden />
          Durability Digital Twin
        </NavLink>
      </nav>
      <div className="mt-auto border-t border-slate-100 p-4 text-[10px] leading-relaxed text-slate-400">
        Williams Sonoma Inc. Sentinel SCM. Internal use.
      </div>
    </aside>
  );
}
