import { useEffect, useState, useCallback } from 'react'
import { getAlerts, resolveAlert } from '../api/endpoints'
import { RefreshCw, CheckCircle2, BellRing } from 'lucide-react'

const SEVERITY_BADGE: Record<string, string> = {
  CRITICAL: 'bg-red-950 text-red-300 border-red-700',
  HIGH: 'bg-orange-950 text-orange-300 border-orange-700',
  WARNING: 'bg-yellow-950 text-yellow-300 border-yellow-700',
  INFO: 'bg-blue-950 text-blue-300 border-blue-700',
}

export default function AlertsPage() {
  const [alerts, setAlerts] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [statusFilter, setStatusFilter] = useState('ACTIVE')
  const [severityFilter, setSeverityFilter] = useState('ALL')
  const [resolvingId, setResolvingId] = useState<number | null>(null)

  const loadData = useCallback(async () => {
    setLoading(true)
    try {
      const data = await getAlerts({
        status: statusFilter,
        severity: severityFilter === 'ALL' ? undefined : severityFilter,
      })
      setAlerts(data)
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }, [statusFilter, severityFilter])

  useEffect(() => { loadData() }, [loadData])

  const handleResolve = async (alertId: number) => {
    setResolvingId(alertId)
    try {
      await resolveAlert(alertId)
      await loadData()
    } catch (e: any) {
      alert(`Failed to resolve alert: ${e.message}`)
    } finally {
      setResolvingId(null)
    }
  }

  const counts = alerts.reduce((acc: Record<string, number>, a) => {
    acc[a.severity] = (acc[a.severity] ?? 0) + 1
    return acc
  }, {})

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-2">
            <BellRing className="w-6 h-6 text-red-400" /> Operational & Sensor Telemetry Alerts
          </h1>
          <p className="text-gray-400 text-sm mt-0.5">
            Automated anomaly detection · Overflow hazards · Stale telemetry · Low battery warnings
          </p>
        </div>
        <button
          onClick={loadData}
          className="flex items-center gap-2 px-3 py-2 bg-gray-800 hover:bg-gray-700 rounded-lg text-sm text-gray-300 transition-colors"
        >
          <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} /> Refresh
        </button>
      </div>

      {/* Severity Counters Summary */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <div className="bg-gray-900 border border-red-900/60 rounded-xl p-4">
          <span className="text-xs text-red-400 font-semibold uppercase tracking-wide">Critical Alerts</span>
          <p className="text-2xl font-bold text-red-300 mt-1">{counts['CRITICAL'] ?? 0}</p>
          <span className="text-[11px] text-gray-500">Immediate dispatch required</span>
        </div>
        <div className="bg-gray-900 border border-orange-900/60 rounded-xl p-4">
          <span className="text-xs text-orange-400 font-semibold uppercase tracking-wide">High Severity</span>
          <p className="text-2xl font-bold text-orange-300 mt-1">{counts['HIGH'] ?? 0}</p>
          <span className="text-[11px] text-gray-500">Threshold exceeded</span>
        </div>
        <div className="bg-gray-900 border border-yellow-900/60 rounded-xl p-4">
          <span className="text-xs text-yellow-400 font-semibold uppercase tracking-wide">Warnings</span>
          <p className="text-2xl font-bold text-yellow-300 mt-1">{counts['WARNING'] ?? 0}</p>
          <span className="text-[11px] text-gray-500">Suspicious telemetry / low power</span>
        </div>
        <div className="bg-gray-900 border border-blue-900/60 rounded-xl p-4">
          <span className="text-xs text-blue-400 font-semibold uppercase tracking-wide">Info / Audits</span>
          <p className="text-2xl font-bold text-blue-300 mt-1">{counts['INFO'] ?? 0}</p>
          <span className="text-[11px] text-gray-500">System notices</span>
        </div>
      </div>

      {/* Filter Bar */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div className="flex gap-2">
          {['ACTIVE', 'RESOLVED', 'ALL'].map((st) => (
            <button
              key={st}
              onClick={() => setStatusFilter(st)}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                statusFilter === st
                  ? 'bg-red-600 text-white'
                  : 'bg-gray-800 text-gray-400 hover:bg-gray-700'
              }`}
            >
              {st} Status
            </button>
          ))}
        </div>

        <div className="flex gap-2">
          {['ALL', 'CRITICAL', 'HIGH', 'WARNING', 'INFO'].map((sev) => (
            <button
              key={sev}
              onClick={() => setSeverityFilter(sev)}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                severityFilter === sev
                  ? 'bg-gray-700 text-white font-bold'
                  : 'bg-gray-800/80 text-gray-400 hover:bg-gray-700'
              }`}
            >
              {sev}
            </button>
          ))}
        </div>
      </div>

      {/* Alerts Table */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
        {alerts.length === 0 ? (
          <div className="p-12 text-center text-gray-500 text-sm">
            <CheckCircle2 className="w-8 h-8 mx-auto mb-2 text-emerald-500/60" />
            No {statusFilter.toLowerCase()} alerts matching current filters.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead className="bg-gray-800 text-gray-400 uppercase tracking-wide">
                <tr>
                  <th className="py-3 px-4 text-left">Alert Type</th>
                  <th className="py-3 px-4 text-center">Severity</th>
                  <th className="py-3 px-4 text-left">Bin Target</th>
                  <th className="py-3 px-4 text-left">Diagnostic Message</th>
                  <th className="py-3 px-4 text-left">Detected At</th>
                  <th className="py-3 px-4 text-center">Status</th>
                  <th className="py-3 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-800 text-gray-300">
                {alerts.map((a) => (
                  <tr key={a.id} className="hover:bg-gray-800/40">
                    <td className="py-3 px-4 font-mono font-bold text-white">{a.alert_type}</td>
                    <td className="py-3 px-4 text-center">
                      <span className={`px-2 py-0.5 rounded text-[11px] font-semibold border ${
                        SEVERITY_BADGE[a.severity] ?? 'bg-gray-800 text-gray-300 border-gray-700'
                      }`}>
                        {a.severity}
                      </span>
                    </td>
                    <td className="py-3 px-4 font-mono text-emerald-400">{a.bin_id || 'SYSTEM'}</td>
                    <td className="py-3 px-4 max-w-[280px]">
                      <p className="text-gray-200 truncate" title={a.message}>{a.message}</p>
                    </td>
                    <td className="py-3 px-4 text-gray-400 font-mono text-[11px]">
                      {new Date(a.created_at).toLocaleString()}
                    </td>
                    <td className="py-3 px-4 text-center">
                      <span className={`px-2 py-0.5 rounded text-[11px] font-semibold ${
                        a.status === 'ACTIVE'
                          ? 'bg-red-950 text-red-300 animate-pulse'
                          : 'bg-emerald-950 text-emerald-300'
                      }`}>
                        {a.status}
                      </span>
                    </td>
                    <td className="py-3 px-4 text-right">
                      {a.status === 'ACTIVE' ? (
                        <button
                          onClick={() => handleResolve(a.id)}
                          disabled={resolvingId === a.id}
                          className="px-2.5 py-1 bg-gray-800 hover:bg-emerald-700 border border-gray-700 hover:border-emerald-600 rounded text-xs text-gray-200 transition-colors"
                        >
                          {resolvingId === a.id ? 'Resolving...' : 'Acknowledge & Resolve'}
                        </button>
                      ) : (
                        <span className="text-gray-500 text-xs">Resolved</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}
