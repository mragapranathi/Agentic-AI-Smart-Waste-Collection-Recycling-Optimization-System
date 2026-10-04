import { useEffect, useState, useCallback } from 'react'
import { getPriorities, calculatePriorities } from '../api/endpoints'
import { Zap, RefreshCw, AlertTriangle } from 'lucide-react'

const PRIORITY_BADGE: Record<string, string> = {
  CRITICAL: 'bg-red-900/80 text-red-300 border-red-700',
  HIGH: 'bg-orange-900/80 text-orange-300 border-orange-700',
  MEDIUM: 'bg-yellow-900/80 text-yellow-300 border-yellow-700',
  LOW: 'bg-emerald-900/80 text-emerald-300 border-emerald-700',
  SENSOR_VERIFICATION_REQUIRED: 'bg-purple-900/80 text-purple-300 border-purple-700',
}

export default function PriorityPage() {
  const [priorities, setPriorities] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [calculating, setCalculating] = useState(false)
  const [filterLevel, setFilterLevel] = useState('ALL')
  const [search, setSearch] = useState('')

  const loadData = useCallback(async () => {
    setLoading(true)
    try {
      const data = await getPriorities()
      setPriorities(data)
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { loadData() }, [loadData])

  const handleRecalculate = async () => {
    setCalculating(true)
    try {
      const data = await calculatePriorities()
      setPriorities(data)
    } catch (e: any) {
      alert(`Calculation error: ${e.message}`)
    } finally {
      setCalculating(false)
    }
  }

  const counts = priorities.reduce((acc: Record<string, number>, p) => {
    acc[p.priority_level] = (acc[p.priority_level] ?? 0) + 1
    return acc
  }, {})

  const filtered = priorities.filter((p) => {
    if (filterLevel !== 'ALL' && p.priority_level !== filterLevel) return false
    if (search && !p.bin_id.toLowerCase().includes(search.toLowerCase()) && !p.location_name.toLowerCase().includes(search.toLowerCase())) {
      return false
    }
    return true
  })

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-2">
            <Zap className="w-6 h-6 text-amber-400" /> Collection Priority Engine
          </h1>
          <p className="text-gray-400 text-sm mt-0.5">
            Deterministic multi-factor scoring engine · Dynamic overflow risk · Explainable decision rules
          </p>
        </div>
        <div className="flex gap-2 flex-wrap">
          <button
            onClick={loadData}
            className="flex items-center gap-2 px-3 py-2 bg-gray-800 hover:bg-gray-700 rounded-lg text-sm text-gray-300 transition-colors"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} /> Refresh
          </button>
          <button
            onClick={handleRecalculate}
            disabled={calculating}
            className="flex items-center gap-2 px-4 py-2 bg-amber-600 hover:bg-amber-500 disabled:opacity-50 rounded-lg text-sm font-semibold text-white transition-colors"
          >
            <Zap className={`w-4 h-4 ${calculating ? 'animate-spin' : ''}`} />
            {calculating ? 'Evaluating Factors...' : 'Recalculate All Priorities'}
          </button>
        </div>
      </div>

      {/* Priority Level Breakdown Summary */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
        {['CRITICAL', 'HIGH', 'MEDIUM', 'LOW', 'SENSOR_VERIFICATION_REQUIRED'].map((lvl) => (
          <div
            key={lvl}
            onClick={() => setFilterLevel(filterLevel === lvl ? 'ALL' : lvl)}
            className={`p-4 rounded-xl border cursor-pointer transition-all ${
              filterLevel === lvl
                ? 'border-amber-500 bg-amber-950/30'
                : 'border-gray-800 bg-gray-900 hover:bg-gray-800/70'
            }`}
          >
            <div className="flex items-center justify-between">
              <span className="text-xs text-gray-400 font-semibold">{lvl.replace(/_/g, ' ')}</span>
              {lvl === 'CRITICAL' && <AlertTriangle className="w-3.5 h-3.5 text-red-400" />}
            </div>
            <p className="text-2xl font-bold text-white mt-1">{counts[lvl] ?? 0}</p>
            <span className="text-[11px] text-gray-500">Click to filter</span>
          </div>
        ))}
      </div>

      {/* Search and Filters Bar */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div className="flex gap-2 flex-wrap">
          {['ALL', 'CRITICAL', 'HIGH', 'MEDIUM', 'LOW', 'SENSOR_VERIFICATION_REQUIRED'].map((lvl) => (
            <button
              key={lvl}
              onClick={() => setFilterLevel(lvl)}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                filterLevel === lvl
                  ? 'bg-amber-600 text-white'
                  : 'bg-gray-800 text-gray-400 hover:bg-gray-700'
              }`}
            >
              {lvl.replace(/_/g, ' ')}
            </button>
          ))}
        </div>
        <input
          type="text"
          placeholder="Search by bin ID or location..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-1.5 text-xs text-gray-200 placeholder-gray-500 focus:outline-none focus:border-amber-500 w-64"
        />
      </div>

      {/* Priority Engine Detailed Registry */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead className="bg-gray-800 text-gray-400 uppercase tracking-wide">
              <tr>
                <th className="py-3 px-4 text-left">Bin ID</th>
                <th className="py-3 px-4 text-left">Location</th>
                <th className="py-3 px-4 text-left">Stream</th>
                <th className="py-3 px-4 text-center">Priority</th>
                <th className="py-3 px-4 text-right">Score</th>
                <th className="py-3 px-4 text-right">Current Fill</th>
                <th className="py-3 px-4 text-right">Predicted (24h)</th>
                <th className="py-3 px-4 text-left">Recommended Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-800 text-gray-300">
              {filtered.map((p) => (
                <tr key={p.bin_id} className="hover:bg-gray-800/40">
                  <td className="py-3 px-4 font-mono font-bold text-white">{p.bin_id}</td>
                  <td className="py-3 px-4 max-w-[160px] truncate" title={p.location_name}>
                    {p.location_name}
                  </td>
                  <td className="py-3 px-4">{p.waste_type}</td>
                  <td className="py-3 px-4 text-center">
                    <span className={`px-2 py-0.5 rounded text-[11px] font-semibold border ${
                      PRIORITY_BADGE[p.priority_level] ?? 'bg-gray-800 text-gray-300 border-gray-700'
                    }`}>
                      {p.priority_level}
                    </span>
                  </td>
                  <td className="py-3 px-4 text-right font-mono font-bold text-amber-400">
                    {p.score?.toFixed(1)}
                  </td>
                  <td className="py-3 px-4 text-right font-medium text-white">
                    {p.current_fill_percent?.toFixed(0)}%
                  </td>
                  <td className="py-3 px-4 text-right text-blue-400">
                    {p.predicted_fill_percent != null ? `${p.predicted_fill_percent.toFixed(0)}%` : '—'}
                  </td>
                  <td className="py-3 px-4">
                    <div className="max-w-[280px]">
                      <p className="font-medium text-gray-200">{p.recommended_action}</p>
                      <p className="text-[11px] text-gray-400 truncate mt-0.5" title={p.reason}>{p.reason}</p>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
