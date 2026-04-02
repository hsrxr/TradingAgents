import { Activity, BarChart3, Bot, ChevronLeft, ChevronRight, ShieldCheck, Workflow } from "lucide-react";

const navItems = [
  { key: "live-pulse", label: "Live Pulse", icon: Activity },
  { key: "market-lens", label: "Market Lens", icon: BarChart3 },
  { key: "agent-mesh", label: "Agent Mesh", icon: Bot },
  { key: "risk-sentinel", label: "Risk Sentinel", icon: ShieldCheck },
  { key: "execution", label: "Execution", icon: Workflow },
];

export type SidebarSectionKey = (typeof navItems)[number]["key"];

type AppSidebarProps = {
  isCollapsed: boolean;
  onToggle: () => void;
  activeSection: SidebarSectionKey;
  onNavigate: (section: SidebarSectionKey) => void;
};

export function AppSidebar({ isCollapsed, onToggle, activeSection, onNavigate }: AppSidebarProps): React.JSX.Element {
  return (
    <aside
      className={`relative hidden border-r border-emerald-500/20 bg-[#09100d]/80 p-2 transition-all duration-300 ease-out md:block ${
        isCollapsed ? "md:w-14" : "md:w-44"
      }`}
    >
      <button
        type="button"
        onClick={onToggle}
        className="absolute right-0 top-4 z-10 translate-x-1/2 rounded-full border border-emerald-500/30 bg-[#0b1410] p-1.5 text-emerald-200 transition-all duration-300 ease-out hover:border-emerald-400/50 hover:bg-emerald-500/10"
        aria-label={isCollapsed ? "Expand sidebar" : "Collapse sidebar"}
      >
        {isCollapsed ? <ChevronRight size={14} /> : <ChevronLeft size={14} />}
      </button>

      <div
        className={`overflow-hidden transition-all duration-300 ease-out ${
          isCollapsed ? "translate-x-1 opacity-0" : "translate-x-0 opacity-100"
        }`}
      >
        <div className="rounded-lg border border-emerald-500/20 bg-[#070d0b] px-2 py-1.5 text-[10px] uppercase tracking-[0.18em] text-emerald-300">
          TradingAgents OS
        </div>
      </div>

      <div className="mt-4 space-y-1.5">
        {navItems.map(({ key, label, icon: Icon }) => (
          <button
            key={key}
            type="button"
            onClick={() => onNavigate(key)}
            className={`flex w-full items-center rounded-md border border-transparent px-2 py-1.5 text-left text-xs text-zinc-300 transition-all duration-300 ease-out hover:border-emerald-500/30 hover:bg-emerald-500/10 hover:text-emerald-200 ${
              isCollapsed ? "justify-center gap-0" : "gap-2"
            } ${
              activeSection === key ? "border-emerald-500/40 bg-emerald-500/15 text-emerald-200" : ""
            }`}
            title={label}
          >
            <Icon size={14} />
            <span
              className={`overflow-hidden whitespace-nowrap transition-all duration-300 ease-out ${
                isCollapsed ? "max-w-0 opacity-0" : "max-w-[120px] opacity-100"
              }`}
            >
              {label}
            </span>
          </button>
        ))}
      </div>
    </aside>
  );
}
