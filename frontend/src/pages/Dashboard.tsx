import { useEffect, useState, useCallback } from 'react'
import { getDashboardKPIs, getAlerts, getVehicles, getBins } from '../api/endpoints'
import {
  Trash2, Truck, AlertTriangle, Recycle, Activity, BarChart3, RefreshCw,
  Clock, Gauge, Route as RouteIcon, ShieldAlert, Cpu
} from 'lucide-react'
import {
  PieChart, Pie, Cell, Tooltip, ResponsiveContainer,
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Legend
} from 'recharts'
import BinMap from '../components/BinMap'

const PRIORITY_COLORS: Record<string, string> = {
  CRITICAL: '#ef4444',
  HIGH: '#f97316',
  MEDIUM: '#eab308',
  LOW: '#22c55e',
  SENSOR_VERIFICATION_REQUIRED: '#8b5cf6',
}

const WASTE_COLORS = ['#22c55e', '#3b82f6', '#f97316', '#8b5cf6']

interface KPI {
  total_bins: number
  bins_requiring_collection: number
  bins_above_threshold?: number
  critical_bins: number
  high_priority_bins?: number
  overflow_risk_bins?: number
  overflow_incidents: number
  vehicles_available: number
  available_vehicles?: number
  active_vehicles: number
  total_vehicles?: number
  total_waste_collected_kg: number
  recycling_rate_percent: number
  average_route_distance_km: number
  collection_efficiency_percent: number
  sensor_failures: number
  average_vehicle_utilization_percent: number
  overflow_rate_percent: number
  active_alerts?: number
  active_alerts_count?: number
  completed_collections_count?: number
  waste_type_distribution?: Record<string, number>
  priority_distribution?: Record<string, number>
}

function KpiCard({
  label, value, sub, icon: Icon, color,
}: {
  label: string; value: string | number; sub?: string; icon: any; color: string
}) {
  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl p-4 flex gap-3.5 items-start hover:border-gray-700 transition-colors">
      <div className={`${color} rounded-lg p-2.5 flex-shrink-0 shadow-sm`}>
        <Icon className="w-5 h-5 text-white" />
      </div>
      <div className="min-w-0 flex-1">
        <p className="text-gray-400 text-[11px] font-medium uppercase tracking-wider">{label}</p>
        <p className="text-xl font-bold text-white mt-0.5 tracking-tight">{value}</p>
        {sub && <p className="text-gray-500 text-xs mt-0.5 truncate">{sub}</p>}
      </div>
    </div>
  )
}

function formatDate(dateStr: string | null | undefined): string {
  if (!dateStr) return 'Recent'
  try {
    const d = new Date(dateStr)
    if (isNaN(d.getTime())) return 'Recent'
    return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }) +
      ' · ' + d.toLocaleDateString([], { month: 'short', day: 'numeric', year: 'numeric' })
  } catch {
    return 'Recent'
  }
}

export default function Dashboard() {
  const [kpis, setKpis] = useState<KPI | null>(null)
  const [alerts, setAlerts] = useState<any[]>([])
  const [vehicles, setVehicles] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [lastRefreshed, setLastRefreshed] = useState<Date>(new Date())
  const [currentTime, setCurrentTime] = useState<Date>(new Date())

  // Keep live clock ticking for accurate real-time telemetry
  useEffect(() => {
    const timer = setInterval(() => setCurrentTime(new Date()), 1000)
    return () => clearInterval(timer)
  }, [])

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const [k, a, v, b] = await Promise.all([
        getDashboardKPIs().catch(() => null),
        getAlerts({ status: 'ACTIVE', limit: 8 }).catch(() => []),
        getVehicles().catch(() => []),
        getBins({ limit: 150 }).catch(() => [])
      ])

      // Fallback distributions if backend KPI didn't include them
      let wasteDist = k?.waste_type_distribution
      let priorityDist = k?.priority_distribution

      if (!wasteDist && b && b.length > 0) {
        wasteDist = {}
        for (const bin of b) {
          const wt = bin.waste_type || 'General'
          wasteDist[wt] = (wasteDist[wt] || 0) + 1
        }
      }

      if (!priorityDist && b && b.length > 0) {
        priorityDist = { CRITICAL: 0, HIGH: 0, MEDIUM: 0, LOW: 0, SENSOR_VERIFICATION_REQUIRED: 0 }
        for (const bin of b) {
          if (['SUSPICIOUS', 'INVALID', 'OFFLINE', 'STALE'].includes(bin.sensor_status)) {
            priorityDist.SENSOR_VERIFICATION_REQUIRED = (priorityDist.SENSOR_VERIFICATION_REQUIRED || 0) + 1
          } else if (bin.current_fill_percent >= 90) {
            priorityDist.CRITICAL = (priorityDist.CRITICAL || 0) + 1
          } else if (bin.current_fill_percent >= (bin.collection_threshold_percent || 85)) {
            priorityDist.HIGH = (priorityDist.HIGH || 0) + 1
          } else if (bin.current_fill_percent >= 50) {
            priorityDist.MEDIUM = (priorityDist.MEDIUM || 0) + 1
          } else {
            priorityDist.LOW = (priorityDist.LOW || 0) + 1
          }
        }
      }

      const availableCount = k?.available_vehicles ?? k?.vehicles_available ?? (v ? v.filter((veh: any) => veh.status === 'AVAILABLE').length : 0)
      const totalVehiclesCount = k?.total_vehicles ?? (v ? v.length : 0)

      setKpis(k ? {
        ...k,
        available_vehicles: availableCount,
        vehicles_available: availableCount,
        total_vehicles: totalVehiclesCount,
        waste_type_distribution: wasteDist,
        priority_distribution: priorityDist,
      } : null)

      setAlerts(a || [])
      setVehicles(v || [])
      setLastRefreshed(new Date())
    } catch (e) {
      console.error('Failed to load dashboard data:', e)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load() }, [load])

  const wasteDistData = kpis?.waste_type_distribution
    ? Object.entries(kpis.waste_type_distribution).map(([name, value]) => ({ name, value }))
    : []

  const priorityDistData = kpis?.priority_distribution
    ? Object.entries(kpis.priority_distribution)
        .filter(([_, value]) => value > 0)
        .map(([name, value]) => ({ name, value, fill: PRIORITY_COLORS[name] ?? '#6b7280' }))
    : []

  return (
    <div className="p-6 space-y-6">
      {/* Header with Live Synchronized Date & Time */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-gray-900/60 border border-gray-800 rounded-xl p-4">
        <div>
          <div className="flex items-center gap-2.5">
            <h1 className="text-2xl font-bold text-white tracking-tight">AI Operations Dashboard</h1>
            <span className="px-2 py-0.5 text-[11px] font-medium bg-emerald-950 text-emerald-400 border border-emerald-800 rounded-full flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
              LIVE TELEMETRY
            </span>
          </div>
          <p className="text-gray-400 text-xs mt-1">Autonomous Multi-Agent Municipal Waste Operations & Fleet Telemetry</p>
        </div>

        <div className="flex items-center gap-4 flex-wrap">
          <div className="text-right">
            <div className="flex items-center gap-1.5 text-xs text-gray-300 font-mono">
              <Clock className="w-3.5 h-3.5 text-emerald-400" />
              <span>{currentTime.toLocaleDateString([], { weekday: 'short', month: 'short', day: 'numeric', year: 'numeric' })}</span>
              <span className="text-emerald-400 font-bold">{currentTime.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}</span>
            </div>
            <p className="text-[11px] text-gray-500 mt-0.5">
              Last synced: {lastRefreshed.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
            </p>
          </div>

          <button
            onClick={load}
            disabled={loading}
            className="flex items-center gap-2 px-3.5 py-2 bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white rounded-lg text-xs font-medium transition-all shadow-sm"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
            Refresh Telemetry
          </button>
        </div>
      </div>

      {/* KPI Cards Grid - All Core Specification Metrics */}
      {kpis ? (
        <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-6 gap-3.5">
          <KpiCard
            label="Total Smart Bins"
            value={kpis.total_bins}
            icon={Trash2}
            color="bg-blue-600"
            sub={`${kpis.bins_requiring_collection ?? kpis.bins_above_threshold ?? 0} above threshold`}
          />
          <KpiCard
            label="Critical Bins"
            value={kpis.critical_bins}
            icon={AlertTriangle}
            color="bg-red-600"
            sub={`${kpis.overflow_risk_bins ?? kpis.overflow_incidents ?? 0} overflow risk`}
          />
          <KpiCard
            label="Vehicles Available"
            value={`${kpis.available_vehicles ?? kpis.vehicles_available ?? 0}/${kpis.total_vehicles ?? vehicles.length ?? 0}`}
            icon={Truck}
            color="bg-emerald-600"
            sub={`${kpis.active_vehicles ?? 0} currently active`}
          />
          <KpiCard
            label="Recycling Rate"
            value={`${(kpis.recycling_rate_percent ?? 0).toFixed(1)}%`}
            icon={Recycle}
            color="bg-purple-600"
            sub="Target: ≥ 45.0%"
          />
          <KpiCard
            label="Collection Efficiency"
            value={`${(kpis.collection_efficiency_percent ?? 0).toFixed(1)}%`}
            icon={Activity}
            color="bg-cyan-600"
            sub="Optimal fulfillment"
          />
          <KpiCard
            label="Active Alerts"
            value={kpis.active_alerts_count ?? kpis.active_alerts ?? alerts.length}
            icon={ShieldAlert}
            color="bg-amber-600"
            sub="Require attention"
          />
          <KpiCard
            label="Total Waste Collected"
            value={`${((kpis.total_waste_collected_kg ?? 0) / 1000).toFixed(1)} t`}
            icon={BarChart3}
            color="bg-indigo-600"
            sub={`${(kpis.total_waste_collected_kg ?? 0).toLocaleString()} kg`}
          />
          <KpiCard
            label="Average Route Distance"
            value={`${(kpis.average_route_distance_km ?? 0).toFixed(1)} km`}
            icon={RouteIcon}
            color="bg-teal-600"
            sub="OR-Tools CVRP optimized"
          />
          <KpiCard
            label="Fleet Utilization"
            value={`${(kpis.average_vehicle_utilization_percent ?? 0).toFixed(1)}%`}
            icon={Gauge}
            color="bg-amber-700"
            sub="Capacity utilized"
          />
          <KpiCard
            label="Sensor Anomalies"
            value={kpis.sensor_failures ?? 0}
            icon={Cpu}
            color="bg-rose-700"
            sub="Stale / Invalid telemetry"
          />
          <KpiCard
            label="Overflow Incidents"
            value={kpis.overflow_incidents ?? 0}
            icon={AlertTriangle}
            color="bg-red-700"
            sub={`Overflow rate: ${(kpis.overflow_rate_percent ?? 0).toFixed(1)}%`}
          />
          <KpiCard
            label="Completed Collections"
            value={kpis.completed_collections_count ?? 0}
            icon={Truck}
            color="bg-green-700"
            sub="Verified pickups"
          />
        </div>
      ) : (
        <div className="p-8 text-center bg-gray-900 border border-gray-800 rounded-xl text-gray-500">
          <RefreshCw className="w-6 h-6 animate-spin mx-auto mb-2 text-emerald-500" />
          Loading Operations KPIs...
        </div>
      )}

      {/* Map + Charts Row */}
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        {/* Map */}
        <div className="xl:col-span-2 bg-gray-900 border border-gray-800 rounded-xl overflow-hidden shadow-sm">
          <div className="px-5 py-3.5 border-b border-gray-800 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="text-sm font-semibold text-white">Live Municipal Bin Telemetry Map</span>
              <span className="text-xs text-gray-500">— OpenStreetMap GIS</span>
            </div>
            <span className="text-[11px] text-gray-400 font-mono">
              {kpis?.total_bins ?? 0} Monitored Bins
            </span>
          </div>
          <div className="h-80">
            <BinMap />
          </div>
        </div>

        {/* Waste Type Pie Chart */}
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-5 flex flex-col justify-between shadow-sm">
          <div className="flex items-center justify-between mb-2">
            <p className="text-sm font-semibold text-white">Waste Type Distribution</p>
            <span className="text-xs text-gray-500">Active fleet breakdown</span>
          </div>
          {wasteDistData.length > 0 ? (
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={wasteDistData}
                    dataKey="value"
                    nameKey="name"
                    cx="50%"
                    cy="48%"
                    outerRadius={80}
                    innerRadius={36}
                    paddingAngle={3}
                    label={({ name, percent }: any) => `${name} ${((percent ?? 0) * 100).toFixed(0)}%`}
                    labelLine={false}
                  >
                    {wasteDistData.map((_, i) => (
                      <Cell key={i} fill={WASTE_COLORS[i % WASTE_COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip
                    contentStyle={{ background: '#0f172a', border: '1px solid #334155', borderRadius: 8, color: '#fff', fontSize: '12px' }}
                    formatter={(val: any, name: any) => [`${val} bins`, name]}
                  />
                  <Legend verticalAlign="bottom" height={36} iconType="circle" />
                </PieChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <div className="h-64 flex flex-col items-center justify-center text-gray-600 text-xs">
              <RefreshCw className="w-5 h-5 mb-2 animate-spin text-gray-600" />
              <span>Compiling waste stream distribution...</span>
            </div>
          )}
        </div>
      </div>

      {/* Priority Distribution + Live Alerts */}
      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
        {/* Priority Bar Chart */}
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-5 shadow-sm">
          <div className="flex items-center justify-between mb-4">
            <div>
              <p className="text-sm font-semibold text-white">Bin Collection Priority Distribution</p>
              <p className="text-xs text-gray-500">Categorized by urgency & sensor health</p>
            </div>
          </div>
          {priorityDistData.length > 0 ? (
            <div className="h-56">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={priorityDistData} margin={{ top: 8, right: 12, left: -16, bottom: 4 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" vertical={false} />
                  <XAxis
                    dataKey="name"
                    tick={{ fill: '#9ca3af', fontSize: 10 }}
                    interval={0}
                    tickFormatter={(val: string) => val === 'SENSOR_VERIFICATION_REQUIRED' ? 'VERIFY' : val}
                  />
                  <YAxis tick={{ fill: '#9ca3af', fontSize: 10 }} />
                  <Tooltip
                    contentStyle={{ background: '#0f172a', border: '1px solid #334155', borderRadius: 8, color: '#fff', fontSize: '12px' }}
                    formatter={(val: any) => [`${val} bins`, 'Count']}
                  />
                  <Bar dataKey="value" radius={[4, 4, 0, 0]}>
                    {priorityDistData.map((entry, i) => (
                      <Cell key={i} fill={entry.fill} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <div className="h-56 flex flex-col items-center justify-center text-gray-600 text-xs">
              <RefreshCw className="w-5 h-5 mb-2 animate-spin text-gray-600" />
              <span>Calculating collection priorities...</span>
            </div>
          )}
        </div>

        {/* Active Real-Time Alerts with Accurate Timestamps */}
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-5 shadow-sm">
          <div className="flex items-center justify-between mb-3.5">
            <div>
              <p className="text-sm font-semibold text-white">Active Operational Alerts</p>
              <p className="text-xs text-gray-500">Real-time anomaly & overflow notifications</p>
            </div>
            <span className="px-2 py-0.5 text-[11px] font-mono bg-red-950 text-red-400 border border-red-800 rounded-full">
              {alerts.length} Active
            </span>
          </div>

          {alerts.length === 0 ? (
            <div className="h-56 flex flex-col items-center justify-center text-gray-500 text-xs">
              <span className="text-emerald-400 font-semibold text-sm mb-1">All Systems Nominal</span>
              <span>No active overflow or sensor alerts recorded.</span>
            </div>
          ) : (
            <div className="space-y-2.5 max-h-56 overflow-y-auto pr-1">
              {alerts.map((a) => (
                <div
                  key={a.id}
                  className={`flex items-start gap-3 p-3 rounded-lg border transition-all ${
                    a.severity === 'CRITICAL' ? 'border-red-800/80 bg-red-950/25' :
                    a.severity === 'HIGH' ? 'border-orange-800/80 bg-orange-950/25' :
                    'border-yellow-800/80 bg-yellow-950/25'
                  }`}
                >
                  <AlertTriangle className={`w-4 h-4 flex-shrink-0 mt-0.5 ${
                    a.severity === 'CRITICAL' ? 'text-red-400' :
                    a.severity === 'HIGH' ? 'text-orange-400' :
                    'text-yellow-400'
                  }`} />
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center justify-between gap-2">
                      <p className="text-xs font-semibold text-gray-200">{a.bin_id || 'SYSTEM'} · <span className="font-mono text-gray-400">{a.alert_type}</span></p>
                      <span className="text-[10px] text-gray-400 font-mono whitespace-nowrap">
                        {formatDate(a.created_at)}
                      </span>
                    </div>
                    <p className="text-xs text-gray-300 mt-0.5 leading-relaxed">{a.message}</p>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Fleet Status Table */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-5 shadow-sm">
        <div className="flex items-center justify-between mb-4">
          <div>
            <p className="text-sm font-semibold text-white">Municipal Fleet Status</p>
            <p className="text-xs text-gray-500">Live vehicle availability, capacity utilization, and waste stream support</p>
          </div>
          <span className="text-xs text-gray-400 font-mono">
            {vehicles.filter(v => v.status === 'AVAILABLE').length} Available / {vehicles.length} Total
          </span>
        </div>

        {vehicles.length === 0 ? (
          <p className="text-gray-600 text-sm py-4">No vehicles registered yet.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-gray-500 text-xs uppercase tracking-wide border-b border-gray-800">
                  <th className="pb-3 pr-4">Vehicle ID</th>
                  <th className="pb-3 pr-4">Status</th>
                  <th className="pb-3 pr-4">Supported Streams</th>
                  <th className="pb-3 pr-4">Max Capacity</th>
                  <th className="pb-3 pr-4">Current Load</th>
                  <th className="pb-3">Utilization</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-800/60">
                {vehicles.slice(0, 10).map((v) => {
                  const utilPct = Math.min(100, Math.round(((v.current_load_liters ?? 0) / (v.capacity_liters ?? 1)) * 100))
                  return (
                    <tr key={v.vehicle_id} className="text-gray-300 hover:bg-gray-800/30">
                      <td className="py-2.5 pr-4 font-mono text-xs text-white font-medium">{v.vehicle_id}</td>
                      <td className="py-2.5 pr-4">
                        <span className={`px-2 py-0.5 rounded text-[11px] font-medium ${
                          v.status === 'AVAILABLE' ? 'bg-emerald-950 text-emerald-300 border border-emerald-800' :
                          v.status === 'ASSIGNED' ? 'bg-blue-950 text-blue-300 border border-blue-800' :
                          v.status === 'IN_TRANSIT' ? 'bg-amber-950 text-amber-300 border border-amber-800' :
                          'bg-gray-800 text-gray-400'
                        }`}>{v.status}</span>
                      </td>
                      <td className="py-2.5 pr-4 text-xs text-gray-400">{(v.supported_waste_types ?? []).join(', ') || 'All Streams'}</td>
                      <td className="py-2.5 pr-4 text-xs font-mono">{v.capacity_liters ? `${v.capacity_liters.toLocaleString()} L` : '-'}</td>
                      <td className="py-2.5 pr-4 text-xs font-mono">{v.current_load_liters ? `${v.current_load_liters.toLocaleString()} L` : '0 L'}</td>
                      <td className="py-2.5 text-xs">
                        <div className="flex items-center gap-2.5">
                          <div className="w-24 bg-gray-800 rounded-full h-1.5 overflow-hidden">
                            <div
                              className={`h-1.5 rounded-full ${
                                utilPct > 85 ? 'bg-red-500' : utilPct > 60 ? 'bg-amber-500' : 'bg-emerald-500'
                              }`}
                              style={{ width: `${utilPct}%` }}
                            />
                          </div>
                          <span className="font-mono text-xs text-gray-400">{utilPct}%</span>
                        </div>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}
