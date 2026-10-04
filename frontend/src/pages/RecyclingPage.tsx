import { useEffect, useState, useCallback } from 'react'
import { getRecyclingAnalytics, getRecyclingRecords } from '../api/endpoints'
import {
  Recycle, RefreshCw, PieChart as PieIcon, ShieldAlert
} from 'lucide-react'
import {
  PieChart, Pie, Cell, Tooltip, ResponsiveContainer,
  BarChart, Bar, XAxis, YAxis, CartesianGrid
} from 'recharts'

const COLORS = ['#10b981', '#3b82f6', '#f59e0b', '#ef4444']

export default function RecyclingPage() {
  const [analytics, setAnalytics] = useState<any | null>(null)
  const [records, setRecords] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [periodDays, setPeriodDays] = useState(30)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const [a, r] = await Promise.all([
        getRecyclingAnalytics({ days: periodDays }),
        getRecyclingRecords({ limit: 50 })
      ])
      setAnalytics(a)
      setRecords(r)
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }, [periodDays])

  useEffect(() => { load() }, [load])

  const wasteData = analytics?.waste_by_type
    ? Object.entries(analytics.waste_by_type).map(([name, value]) => ({ name, value }))
    : []

  const zoneData = analytics?.contamination_by_zone
    ? Object.entries(analytics.contamination_by_zone).map(([zone, rate]) => ({
        zone,
        rate: Number(Number(rate).toFixed(1)),   // API already returns %, do not multiply by 100
      }))
    : []

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-2">
            <Recycle className="w-6 h-6 text-emerald-400" /> Recycling Performance & Segregation
          </h1>
          <p className="text-gray-400 text-sm mt-0.5">
            Audit segregation compliance · Track contamination trends · Diversion metrics
          </p>
        </div>
        <div className="flex gap-2 flex-wrap items-center">
          <select
            value={periodDays}
            onChange={(e) => setPeriodDays(Number(e.target.value))}
            className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-xs text-gray-200 focus:outline-none focus:border-emerald-500"
          >
            <option value={7}>Last 7 Days</option>
            <option value={30}>Last 30 Days</option>
            <option value={90}>Last 90 Days</option>
          </select>
          <button
            onClick={load}
            className="flex items-center gap-2 px-3 py-2 bg-gray-800 hover:bg-gray-700 rounded-lg text-sm text-gray-300 transition-colors"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} /> Refresh
          </button>
        </div>
      </div>

      {/* KPI Cards */}
      {analytics && (
        <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-6 gap-3">
          <div className="bg-gray-900 border border-gray-800 rounded-xl p-4">
            <span className="text-xs text-gray-500 uppercase tracking-wide">Total Waste</span>
            <p className="text-xl font-bold text-white mt-1">{(analytics.total_waste_kg / 1000).toFixed(1)} t</p>
            <span className="text-[11px] text-gray-400">{analytics.total_waste_kg.toFixed(0)} kg</span>
          </div>

          <div className="bg-gray-900 border border-emerald-900/50 rounded-xl p-4">
            <span className="text-xs text-emerald-400 uppercase tracking-wide font-semibold">Recycling Rate</span>
            <p className="text-xl font-bold text-emerald-300 mt-1">
              {(analytics.recycling_rate_percent ?? 0).toFixed(1)}%
            </p>
            <span className="text-[11px] text-emerald-500">Target: ≥ 45%</span>
          </div>

          <div className="bg-gray-900 border border-gray-800 rounded-xl p-4">
            <span className="text-xs text-blue-400 uppercase tracking-wide">Recyclables</span>
            <p className="text-xl font-bold text-white mt-1">{(analytics.recyclable_kg / 1000).toFixed(1)} t</p>
            <span className="text-[11px] text-gray-400">{analytics.recyclable_kg.toFixed(0)} kg</span>
          </div>

          <div className="bg-gray-900 border border-gray-800 rounded-xl p-4">
            <span className="text-xs text-green-400 uppercase tracking-wide">Organic Waste</span>
            <p className="text-xl font-bold text-white mt-1">{(analytics.organic_kg / 1000).toFixed(1)} t</p>
            <span className="text-[11px] text-gray-400">{analytics.organic_kg.toFixed(0)} kg</span>
          </div>

          <div className="bg-gray-900 border border-gray-800 rounded-xl p-4">
            <span className="text-xs text-gray-400 uppercase tracking-wide">General Landfill</span>
            <p className="text-xl font-bold text-white mt-1">{(analytics.general_kg / 1000).toFixed(1)} t</p>
            <span className="text-[11px] text-gray-400">{analytics.general_kg.toFixed(0)} kg</span>
          </div>

          <div className="bg-gray-900 border border-amber-900/50 rounded-xl p-4">
            <span className="text-xs text-amber-400 uppercase tracking-wide font-semibold">Avg Contamination</span>
            <p className="text-xl font-bold text-amber-300 mt-1">
              {(analytics.average_contamination_percent ?? 0).toFixed(1)}%
            </p>
            <span className="text-[11px] text-amber-500">Tolerance: &lt; 10%</span>
          </div>
        </div>
      )}

      {/* Charts Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Waste Composition Pie */}
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
          <div className="flex items-center gap-2 mb-4">
            <PieIcon className="w-4 h-4 text-emerald-400" />
            <h2 className="text-sm font-bold text-white">Stream Composition (kg)</h2>
          </div>
          {wasteData.length > 0 ? (
            <ResponsiveContainer width="100%" height={260}>
              <PieChart>
                <Pie
                  data={wasteData}
                  dataKey="value"
                  nameKey="name"
                  cx="50%"
                  cy="50%"
                  outerRadius={95}
                  label={({ name, percent }: any) => `${name} ${((percent ?? 0) * 100).toFixed(0)}%`}
                >
                  {wasteData.map((_, i) => (
                    <Cell key={i} fill={COLORS[i % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip
                  formatter={(val: any) => `${Number(val).toFixed(0)} kg`}
                  contentStyle={{ background: '#1f2937', border: 'none', borderRadius: 8, color: '#fff' }}
                />
              </PieChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-64 flex items-center justify-center text-gray-500 text-sm">No data</div>
          )}
        </div>

        {/* Contamination by Zone Bar Chart */}
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
          <div className="flex items-center gap-2 mb-4">
            <ShieldAlert className="w-4 h-4 text-amber-400" />
            <h2 className="text-sm font-bold text-white">Contamination Rate by Municipal Zone (%)</h2>
          </div>
          {zoneData.length > 0 ? (
            <ResponsiveContainer width="100%" height={260}>
              <BarChart data={zoneData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                <XAxis dataKey="zone" tick={{ fill: '#9ca3af', fontSize: 10 }} />
                <YAxis unit="%" tick={{ fill: '#9ca3af', fontSize: 10 }} />
                <Tooltip
                  formatter={(val: any) => `${val}%`}
                  contentStyle={{ background: '#1f2937', border: 'none', borderRadius: 8, color: '#fff' }}
                />
                <Bar dataKey="rate" fill="#f59e0b" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-64 flex items-center justify-center text-gray-500 text-sm">No zone data available</div>
          )}
        </div>
      </div>

      {/* Recent Recycling Audit Records */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
        <h2 className="text-sm font-bold text-white mb-4">Recent Facility Weight & Segregation Audit Records</h2>
        <div className="overflow-x-auto rounded-lg border border-gray-800">
          <table className="w-full text-xs">
            <thead className="bg-gray-800 text-gray-400">
              <tr>
                <th className="py-2.5 px-3 text-left">Record ID</th>
                <th className="py-2.5 px-3 text-left">Collection ID</th>
                <th className="py-2.5 px-3 text-left">Waste Stream</th>
                <th className="py-2.5 px-3 text-right">Total Weight</th>
                <th className="py-2.5 px-3 text-right">Recyclable Portion</th>
                <th className="py-2.5 px-3 text-right">Contamination</th>
                <th className="py-2.5 px-3 text-center">Quality Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-800 text-gray-300">
              {records.map((r) => {
                const contaminationPct = r.weight_kg > 0 ? (r.contamination_weight_kg / r.weight_kg) * 100 : 0
                const isAcceptable = contaminationPct < 15
                return (
                  <tr key={r.id} className="hover:bg-gray-800/40">
                    <td className="py-2.5 px-3 font-mono text-gray-500">#{r.id}</td>
                    <td className="py-2.5 px-3 font-mono text-white font-medium">{r.collection_id}</td>
                    <td className="py-2.5 px-3">{r.waste_type}</td>
                    <td className="py-2.5 px-3 text-right font-medium text-white">{r.weight_kg.toFixed(1)} kg</td>
                    <td className="py-2.5 px-3 text-right text-emerald-400 font-medium">{r.recyclable_weight_kg.toFixed(1)} kg</td>
                    <td className="py-2.5 px-3 text-right text-amber-400 font-medium">
                      {r.contamination_weight_kg.toFixed(1)} kg ({contaminationPct.toFixed(1)}%)
                    </td>
                    <td className="py-2.5 px-3 text-center">
                      <span className={`px-2 py-0.5 rounded text-[11px] font-semibold ${
                        isAcceptable ? 'bg-emerald-950 text-emerald-300' : 'bg-red-950 text-red-300'
                      }`}>
                        {isAcceptable ? 'PASSED' : 'CONTAMINATED'}
                      </span>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
