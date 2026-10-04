import { useEffect, useState, useCallback } from 'react'
import { getCollections, updateCollection } from '../api/endpoints'
import { CheckCircle2, RefreshCw, Truck, ArrowRight } from 'lucide-react'

const STATUS_BADGE: Record<string, string> = {
  PLANNED: 'bg-gray-800 text-gray-300 border-gray-700',
  PENDING: 'bg-gray-800 text-gray-300 border-gray-700',
  ASSIGNED: 'bg-blue-900/60 text-blue-300 border-blue-700',
  APPROVED: 'bg-indigo-900/60 text-indigo-300 border-indigo-700',
  EN_ROUTE: 'bg-amber-900/60 text-amber-300 border-amber-700',
  ARRIVED: 'bg-yellow-900/60 text-yellow-300 border-yellow-700',
  COLLECTING: 'bg-cyan-900/60 text-cyan-300 border-cyan-700',
  COLLECTED: 'bg-emerald-900/60 text-emerald-300 border-emerald-700',
  VERIFIED: 'bg-emerald-900/60 text-emerald-300 border-emerald-700',
  COMPLETED: 'bg-emerald-900/60 text-emerald-300 border-emerald-700',
  FAILED: 'bg-red-900/60 text-red-300 border-red-700',
  CANCELLED: 'bg-red-900/60 text-red-300 border-red-700',
}

const LIFECYCLE_OPTIONS = [
  'PENDING',
  'ASSIGNED',
  'EN_ROUTE',
  'ARRIVED',
  'COLLECTING',
  'COMPLETED',
  'FAILED',
  'CANCELLED',
]

export default function CollectionsPage() {
  const [collections, setCollections] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [statusFilter, setStatusFilter] = useState('ALL')
  const [search, setSearch] = useState('')
  const [updatingId, setUpdatingId] = useState<string | null>(null)
  const [actionMessage, setActionMessage] = useState<string | null>(null)

  const loadData = useCallback(async () => {
    setLoading(true)
    try {
      const data = await getCollections({ limit: 150 })
      setCollections(data)
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { loadData() }, [loadData])

  const handleUpdateStatus = async (collectionId: string, newStatus: string, estVolume: number) => {
    setUpdatingId(collectionId)
    setActionMessage(null)
    try {
      await updateCollection(collectionId, {
        status: newStatus,
        actual_volume: estVolume,
        operator_comment: `Status updated to ${newStatus} via Dispatcher console.`,
      })
      setActionMessage(`Collection ${collectionId} transitioned to ${newStatus}`)
      await loadData()
    } catch (e: any) {
      alert(`Status update failed: ${e.response?.data?.detail || e.message}`)
    } finally {
      setUpdatingId(null)
    }
  }

  const handleAdvanceStatus = async (collectionId: string, currentStatus: string, estVolume: number) => {
    let nextStatus = 'COMPLETED'
    if (['PLANNED', 'PENDING', 'APPROVED'].includes(currentStatus)) {
      nextStatus = 'EN_ROUTE'
    } else if (['EN_ROUTE', 'ASSIGNED'].includes(currentStatus)) {
      nextStatus = 'ARRIVED'
    } else if (currentStatus === 'ARRIVED') {
      nextStatus = 'COLLECTING'
    } else if (currentStatus === 'COLLECTING') {
      nextStatus = 'COMPLETED'
    }
    await handleUpdateStatus(collectionId, nextStatus, estVolume)
  }

  const filtered = collections.filter((c) => {
    if (statusFilter !== 'ALL' && c.status !== statusFilter) return false
    if (search && !c.bin_id.toLowerCase().includes(search.toLowerCase()) && !c.vehicle_id.toLowerCase().includes(search.toLowerCase()) && !c.collection_id.toLowerCase().includes(search.toLowerCase())) {
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
            <CheckCircle2 className="w-6 h-6 text-emerald-400" /> Collection Tracking & Dispatch Lifecycle
          </h1>
          <p className="text-gray-400 text-sm mt-0.5">
            Full operational lifecycle tracking · State transitions: PENDING &rarr; ASSIGNED &rarr; EN_ROUTE &rarr; ARRIVED &rarr; COLLECTING &rarr; COMPLETED
          </p>
        </div>
        <button
          onClick={loadData}
          className="flex items-center gap-2 px-3 py-2 bg-gray-800 hover:bg-gray-700 rounded-lg text-sm text-gray-300 transition-colors"
        >
          <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} /> Refresh
        </button>
      </div>

      {actionMessage && (
        <div className="p-3 bg-emerald-950/60 border border-emerald-800 rounded-lg text-xs text-emerald-300 flex items-center justify-between">
          <span>✓ {actionMessage}</span>
          <button onClick={() => setActionMessage(null)} className="text-gray-400 hover:text-white">✕</button>
        </div>
      )}

      {/* Filter and Search Bar */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div className="flex gap-1.5 flex-wrap">
          {['ALL', 'APPROVED', 'ASSIGNED', 'EN_ROUTE', 'ARRIVED', 'COLLECTING', 'COMPLETED', 'FAILED'].map((st) => (
            <button
              key={st}
              onClick={() => setStatusFilter(st)}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                statusFilter === st
                  ? 'bg-emerald-600 text-white'
                  : 'bg-gray-800 text-gray-400 hover:bg-gray-700'
              }`}
            >
              {st}
            </button>
          ))}
        </div>
        <input
          type="text"
          placeholder="Filter by ID, Bin, or Vehicle..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-1.5 text-xs text-gray-200 placeholder-gray-500 focus:outline-none focus:border-emerald-500 w-64"
        />
      </div>

      {/* Collections Lifecycle Table */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead className="bg-gray-800 text-gray-400 uppercase tracking-wide">
              <tr>
                <th className="py-3 px-4 text-left">Collection ID</th>
                <th className="py-3 px-4 text-left">Bin Target</th>
                <th className="py-3 px-4 text-left">Assigned Fleet</th>
                <th className="py-3 px-4 text-left">Route ID</th>
                <th className="py-3 px-4 text-right">Est. Volume</th>
                <th className="py-3 px-4 text-center">Lifecycle Status</th>
                <th className="py-3 px-4 text-center">Manual State Change</th>
                <th className="py-3 px-4 text-right">Primary Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-800 text-gray-300">
              {filtered.map((c) => {
                const isFinished = ['COLLECTED', 'VERIFIED', 'COMPLETED'].includes(c.status)
                const isBusy = updatingId === c.collection_id

                return (
                  <tr key={c.collection_id} className="hover:bg-gray-800/40">
                    <td className="py-3 px-4 font-mono font-bold text-white">{c.collection_id}</td>
                    <td className="py-3 px-4 font-mono text-emerald-400">{c.bin_id}</td>
                    <td className="py-3 px-4 font-mono text-blue-400">{c.vehicle_id}</td>
                    <td className="py-3 px-4 font-mono text-gray-400">{c.route_id || '—'}</td>
                    <td className="py-3 px-4 text-right font-medium">{c.estimated_volume?.toFixed(0)} L</td>
                    <td className="py-3 px-4 text-center">
                      <span className={`px-2 py-0.5 rounded text-[11px] font-semibold border ${
                        STATUS_BADGE[c.status] ?? 'bg-gray-800 text-gray-300 border-gray-700'
                      }`}>
                        {c.status}
                      </span>
                    </td>
                    <td className="py-3 px-4 text-center">
                      <select
                        value={c.status}
                        disabled={isBusy}
                        onChange={(e) => handleUpdateStatus(c.collection_id, e.target.value, c.estimated_volume)}
                        className="bg-gray-800 border border-gray-700 rounded px-2 py-1 text-[11px] text-gray-200 focus:outline-none focus:border-emerald-500"
                      >
                        {LIFECYCLE_OPTIONS.map((opt) => (
                          <option key={opt} value={opt}>{opt}</option>
                        ))}
                      </select>
                    </td>
                    <td className="py-3 px-4 text-right">
                      {!isFinished ? (
                        <button
                          onClick={() => handleAdvanceStatus(c.collection_id, c.status, c.estimated_volume)}
                          disabled={isBusy}
                          className="inline-flex items-center gap-1 px-2.5 py-1 bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 rounded text-xs font-semibold text-white transition-colors"
                        >
                          {isBusy ? (
                            'Advancing...'
                          ) : ['PLANNED', 'PENDING', 'APPROVED'].includes(c.status) ? (
                            <>Dispatch En Route <Truck className="w-3 h-3" /></>
                          ) : c.status === 'EN_ROUTE' ? (
                            <>Mark Arrived <ArrowRight className="w-3 h-3" /></>
                          ) : c.status === 'ARRIVED' ? (
                            <>Start Collecting <ArrowRight className="w-3 h-3" /></>
                          ) : c.status === 'COLLECTING' ? (
                            <>Complete Collection <CheckCircle2 className="w-3 h-3" /></>
                          ) : (
                            <>Advance <ArrowRight className="w-3 h-3" /></>
                          )}
                        </button>
                      ) : (
                        <span className="text-gray-500 text-xs font-medium flex items-center justify-end gap-1">
                          <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" /> Done
                        </span>
                      )}
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
