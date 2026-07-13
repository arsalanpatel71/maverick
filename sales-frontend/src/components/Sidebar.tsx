import { Link, useLocation } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import Logo from "./Logo";

function HomeIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="w-[18px] h-[18px]">
      <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" />
      <polyline points="9,22 9,12 15,12 15,22" />
    </svg>
  );
}

function BotIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="w-[18px] h-[18px]">
      <rect x="3" y="11" width="18" height="10" rx="2" />
      <circle cx="12" cy="5" r="2" />
      <path d="M12 7v4" />
      <circle cx="8.5" cy="16.5" r="1" fill="currentColor" stroke="none" />
      <circle cx="15.5" cy="16.5" r="1" fill="currentColor" stroke="none" />
    </svg>
  );
}

function DatabaseIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="w-[18px] h-[18px]">
      <ellipse cx="12" cy="5" rx="9" ry="3" />
      <path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3" />
      <path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5" />
    </svg>
  );
}

function CreditsIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="w-[18px] h-[18px]">
      <circle cx="12" cy="12" r="9" />
      <path d="M14.8 9.2A3 3 0 0 0 9 11v2a3 3 0 0 0 5.8.8" />
    </svg>
  );
}

function SkillsIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="w-[18px] h-[18px]">
      <path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z" />
    </svg>
  );
}

function AdminIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="w-[18px] h-[18px]">
      <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
      <circle cx="9" cy="7" r="4" />
      <path d="M23 21v-2a4 4 0 0 0-3-3.87" />
      <path d="M16 3.13a4 4 0 0 1 0 7.75" />
    </svg>
  );
}

function LogoutIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="w-[18px] h-[18px]">
      <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
      <polyline points="16,17 21,12 16,7" />
      <line x1="21" y1="12" x2="9" y2="12" />
    </svg>
  );
}

function ChevronLeftIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="w-4 h-4">
      <polyline points="15,18 9,12 15,6" />
    </svg>
  );
}

function ChevronRightIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="w-4 h-4">
      <polyline points="9,18 15,12 9,6" />
    </svg>
  );
}

function NavItem({ to, icon, label, collapsed }: { to: string; icon: React.ReactNode; label: string; collapsed: boolean }) {
  const { pathname } = useLocation();
  const active = to === "/" ? pathname === "/" : pathname.startsWith(to);

  return (
    <Link
      to={to}
      title={collapsed ? label : undefined}
      className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-all duration-150 ${
        active
          ? "bg-accent-faint text-accent font-medium"
          : "text-muted hover:text-slate-700 hover:bg-black/5"
      }`}
    >
      <span className="flex-shrink-0">{icon}</span>
      {!collapsed && <span className="font-medium truncate leading-none">{label}</span>}
    </Link>
  );
}

export default function Sidebar({ collapsed, onToggle }: { collapsed: boolean; onToggle: () => void }) {
  const { user, logout } = useAuth();

  return (
    <div
      className={`flex-shrink-0 flex flex-col border-r border-border bg-surface-alt transition-all duration-200 ${
        collapsed ? "w-14" : "w-56"
      }`}
      style={{ overflow: "hidden" }}
    >
      {/* Brand */}
      <div className={`flex items-center border-b border-border px-3 py-4 ${collapsed ? "flex-col gap-2" : "justify-between gap-3"}`}>
        <div className="flex items-center gap-3 min-w-0">
          <div className="w-8 h-8 rounded-lg bg-purple-gradient flex items-center justify-center flex-shrink-0 shadow-sm">
            <Logo size="sm" />
          </div>
          {!collapsed && (
            <p className="text-slate-900 font-semibold text-sm tracking-widest leading-none truncate">MAVERICK</p>
          )}
        </div>
        <button
          onClick={onToggle}
          title={collapsed ? "Expand sidebar" : "Collapse sidebar"}
          className="flex-shrink-0 w-6 h-6 flex items-center justify-center rounded-md text-muted hover:text-slate-700 hover:bg-black/5 transition-all duration-150"
        >
          {collapsed ? <ChevronRightIcon /> : <ChevronLeftIcon />}
        </button>
      </div>

      {/* Nav */}
      <nav className="flex-1 p-2 space-y-0.5">
        <NavItem to="/"       icon={<HomeIcon />}     label="Home"    collapsed={collapsed} />
        <NavItem to="/agents" icon={<BotIcon />}      label="Agents"  collapsed={collapsed} />
        <NavItem to="/rags"   icon={<DatabaseIcon />} label="RAGs"    collapsed={collapsed} />
        <NavItem to="/skills" icon={<SkillsIcon />}   label="Skills"  collapsed={collapsed} />
        <NavItem to="/credits" icon={<CreditsIcon />} label="Credits" collapsed={collapsed} />
        {user?.role === "super_admin" && (
          <NavItem to="/admin" icon={<AdminIcon />}   label="Admin"   collapsed={collapsed} />
        )}
      </nav>

      {/* User + Logout */}
      <div className="border-t border-border p-2">
        {!collapsed && user && (
          <div className="px-3 py-2 mb-1">
            <p className="text-xs font-medium text-slate-700 truncate">{user.name}</p>
            <p className="text-[10px] text-muted truncate">{user.email}</p>
          </div>
        )}
        <button
          onClick={logout}
          title={collapsed ? "Sign out" : undefined}
          className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm text-muted hover:text-red-500 hover:bg-red-50 transition-all duration-150"
        >
          <span className="flex-shrink-0"><LogoutIcon /></span>
          {!collapsed && <span className="font-medium">Sign out</span>}
        </button>
      </div>
    </div>
  );
}
