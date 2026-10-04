import { NavLink, Outlet } from 'react-router-dom'
import {
  LayoutDashboard,
  Trash2,
  Truck,
  MapPin,
  Workflow,
  Recycle,
  FileText,
  Map as MapIcon,
  Zap,
  TrendingUp,
  CheckCircle2,
  BellRing,
} from 'lucide-react'

const navItems = [
  { to: '/', label: 'Dashboard', icon: LayoutDashboard, end: true },
  { to: '/bins', label: 'Smart Bins', icon: Trash2 },
  { to: '/map', label: 'Live Map', icon: MapIcon },
  { to: '/priority', label: 'Priority Engine', icon: Zap },
  { to: '/forecasting', label: 'Forecasting', icon: TrendingUp },
  { to: '/vehicles', label: 'Vehicles', icon: Truck },
  { to: '/routes', label: 'Routes', icon: MapPin },
  { to: '/collections', label: 'Collections', icon: CheckCircle2 },
  { to: '/recycling', label: 'Recycling', icon: Recycle },
  { to: '/alerts', label: 'Sensor Alerts', icon: BellRing },
  { to: '/workflows', label: 'Workflows', icon: Workflow },
  { to: '/reports', label: 'Reports', icon: FileText },
]

export default function Layout() {
  return (
    <div className="flex h-screen bg-gray-950 text-gray-100 overflow-hidden">
      {/* Sidebar */}
      <aside className="w-64 flex-shrink-0 bg-gray-900 border-r border-gray-800 flex flex-col">
        {/* Brand */}
        <div className="flex items-center gap-3 px-4 py-4 border-b border-gray-800 bg-gray-950/50">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-emerald-500/20 via-teal-500/10 to-blue-500/20 border border-emerald-500/40 flex items-center justify-center p-1.5 shadow-sm flex-shrink-0">
            <img src="/favicon.svg" alt="Agentic AI Smart Waste" className="w-full h-full object-contain" />
          </div>
          <div className="min-w-0 flex-1">
            <p className="font-bold text-white text-[11px] leading-snug tracking-tight">
              Agentic AI Smart Waste Collection &amp; Recycling Optimization System
            </p>
          </div>
        </div>

        {/* Nav */}
        <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
          {navItems.map(({ to, label, icon: Icon, end }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                  isActive
                    ? 'bg-emerald-600 text-white'
                    : 'text-gray-400 hover:bg-gray-800 hover:text-gray-200'
                }`
              }
            >
              <Icon className="w-4 h-4 flex-shrink-0" />
              {label}
            </NavLink>
          ))}
        </nav>

        {/* Footer */}
        <div className="px-4 py-4 border-t border-gray-800">
          <p className="text-xs text-gray-500">v1.0.0 · Demo Mode</p>
        </div>
      </aside>

      {/* Main content */}
      <main className="flex-1 overflow-y-auto">
        <Outlet />
      </main>
    </div>
  )
}
