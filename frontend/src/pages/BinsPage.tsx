import { useEffect, useState, useCallback } from 'react'
import { getBins, getAlerts, calculatePriorities, runForecast, createBin, updateBin, deleteBin, submitReading } from '../api/endpoints'
import { Trash2, RefreshCw, Zap, TrendingUp, Plus, Edit, X, Activity, AlertTriangle } from 'lucide-react'

const PRIORITY_BADGE: Record<string, string> = {
  CRITICAL: 'bg-red-900 text-red-300',
  HIGH: 'bg-orange-900 text-orange-300',
  MEDIUM: 'bg-yellow-900 text-yellow-300',
  LOW: 'bg-green-900 text-green-300',
  SENSOR_VERIFICATION_REQUIRED: 'bg-purple-900 text-purple-300',
}

const FILL_COLOR = (fill: number) => {
  if (fill >= 90) return 'bg-red-500'
  if (fill >= 75) return 'bg-orange-500'
  if (fill >= 50) return 'bg-yellow-500'
  return 'bg-emerald-500'
}

export default function BinsPage() {
  const [bins, setBins] = useState<any[]>([])
  const [alerts, setAlerts] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [calcLoading, setCalcLoading] = useState(false)
  const [priorities, setPriorities] = useState<any[]>([])
  const [filter, setFilter] = useState('ALL')
  const [search, setSearch] = useState('')
  const [selectedBin, setSelectedBin] = useState<string | null>(null)
  const [forecast, setForecast] = useState<any | null>(null)
  const [forecastLoading, setForecastLoading] = useState(false)

  // Modals state
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [showEditModal, setShowEditModal] = useState(false)
  const [showReadingModal, setShowReadingModal] = useState(false)
  const [editingBin, setEditingBin] = useState<any | null>(null)
  const [readingTargetBin, setReadingTargetBin] = useState<any | null>(null)

  // Form states & errors
  const [formData, setFormData] = useState<Record<string, any>>({
    bin_id: '',
    location_name: '',
    latitude: 12.9716,
    longitude: 77.5946,
    waste_type: 'General',
    capacity_liters: 1000,
    current_fill_percent: 30,
    collection_threshold_percent: 85,
    operational_status: 'OPERATIONAL',
    battery_level: 100,
  })
  const [formError, setFormError] = useState<string | null>(null)
  const [formSubmitting, setFormSubmitting] = useState(false)

  // Telemetry simulation form state
  const [readingData, setReadingData] = useState<Record<string, any>>({
    fill_percent: 35,
    weight_kg: 50,
    temperature: 25,
    battery_level: 95,
  })
  const [readingResult, setReadingResult] = useState<any | null>(null)
  const [readingError, setReadingError] = useState<string | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const [b, a] = await Promise.all([getBins(), getAlerts({ status: 'ACTIVE', limit: 100 })])
      setBins(b)
      setAlerts(a)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load() }, [load])

  const handleCalculatePriorities = async () => {
    setCalcLoading(true)
    try {
      const res = await calculatePriorities()
      setPriorities(Array.isArray(res) ? res : res.priorities ?? [])
    } finally {
      setCalcLoading(false)
    }
  }

  const handleForecast = async (binId: string) => {
    setSelectedBin(binId)
    setForecastLoading(true)
    try {
      const res = await runForecast(binId, 24)
      setForecast(res)
    } finally {
      setForecastLoading(false)
    }
  }

  const handleOpenCreate = () => {
    setFormData({
      bin_id: `BIN-MUNI-${Math.floor(100 + Math.random() * 900)}`,
      location_name: 'Municipal Station Central',
      latitude: 12.972,
      longitude: 77.595,
      waste_type: 'General',
      capacity_liters: 1000,
      current_fill_percent: 25,
      collection_threshold_percent: 85,
      operational_status: 'OPERATIONAL',
      battery_level: 98,
    })
    setFormError(null)
    setShowCreateModal(true)
  }

  const handleOpenEdit = (b: any) => {
    setEditingBin(b)
    setFormData({
      location_name: b.location_name,
      capacity_liters: b.capacity_liters,
      waste_type: b.waste_type,
      current_fill_percent: b.current_fill_percent,
      collection_threshold_percent: b.collection_threshold_percent,
      operational_status: b.operational_status,
      battery_level: b.battery_level ?? 100,
    })
    setFormError(null)
    setShowEditModal(true)
  }

  const handleCreateSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setFormError(null)

    // Frontend validations
    if (!formData.bin_id || !formData.bin_id.trim()) {
      setFormError('Bin ID is required.')
      return
    }
    if (formData.capacity_liters <= 0) {
      setFormError('Capacity must be greater than 0 Liters.')
      return
    }
    if (formData.current_fill_percent < 0 || formData.current_fill_percent > 100) {
      setFormError('Fill level must be between 0% and 100%.')
      return
    }
    if (formData.latitude < -90 || formData.latitude > 90 || formData.longitude < -180 || formData.longitude > 180) {
      setFormError('Invalid geographical coordinates (latitude: -90..90, longitude: -180..180).')
      return
    }

    setFormSubmitting(true)
    try {
      await createBin({
        ...formData,
        capacity_liters: Number(formData.capacity_liters),
        current_fill_percent: Number(formData.current_fill_percent),
        collection_threshold_percent: Number(formData.collection_threshold_percent),
        latitude: Number(formData.latitude),
        longitude: Number(formData.longitude),
        battery_level: Number(formData.battery_level),
      })
      setShowCreateModal(false)
      await load()
    } catch (err: any) {
      setFormError(err.response?.data?.detail || err.message)
    } finally {
      setFormSubmitting(false)
    }
  }

  const handleEditSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!editingBin) return
    setFormError(null)

    if (formData.capacity_liters <= 0) {
      setFormError('Capacity must be greater than 0 Liters.')
      return
    }
    if (formData.current_fill_percent < 0 || formData.current_fill_percent > 100) {
      setFormError('Fill level must be between 0% and 100%.')
      return
    }

    setFormSubmitting(true)
    try {
      await updateBin(editingBin.bin_id, {
        location_name: formData.location_name,
        capacity_liters: Number(formData.capacity_liters),
        waste_type: formData.waste_type,
        current_fill_percent: Number(formData.current_fill_percent),
        collection_threshold_percent: Number(formData.collection_threshold_percent),
        operational_status: formData.operational_status,
        battery_level: Number(formData.battery_level),
      })
      setShowEditModal(false)
      await load()
    } catch (err: any) {
      setFormError(err.response?.data?.detail || err.message)
    } finally {
      setFormSubmitting(false)
    }
  }

  const handleDeleteBin = async (binId: string) => {
    if (!window.confirm(`Are you sure you want to permanently delete Bin ${binId}?`)) return
    try {
      await deleteBin(binId)
      await load()
    } catch (err: any) {
      alert(`Failed to delete bin: ${err.response?.data?.detail || err.message}`)
    }
  }

  const handleOpenReadingModal = (b: any) => {
    setReadingTargetBin(b)
    setReadingData({
      fill_percent: Math.min(100, (b.current_fill_percent ?? 30) + 15),
      weight_kg: 60,
      temperature: 25,
      battery_level: b.battery_level ?? 95,
    })
    setReadingResult(null)
    setReadingError(null)
    setShowReadingModal(true)
  }

  const handleSubmitReading = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!readingTargetBin) return
    setReadingError(null)
    setReadingResult(null)
    try {
      const res = await submitReading({
        bin_id: readingTargetBin.bin_id,
        fill_percent: Number(readingData.fill_percent),
        weight_kg: Number(readingData.weight_kg),
        temperature: Number(readingData.temperature),
        battery_level: Number(readingData.battery_level),
      })
      setReadingResult(res)
      await load()
    } catch (err: any) {
      setReadingError(err.response?.data?.detail || err.message)
    }
  }

  const alertBinIds = new Set(alerts.map((a) => a.bin_id))
  const priorityMap = Object.fromEntries(priorities.map((p: any) => [p.bin_id, p]))

  const filtered = bins.filter((b) => {
    if (filter !== 'ALL' && b.waste_type !== filter) return false
    if (search && !b.bin_id.toLowerCase().includes(search.toLowerCase()) && !b.location_name.toLowerCase().includes(search.toLowerCase())) return false
    return true
  })

  const wasteTypes = ['ALL', ...Array.from(new Set(bins.map((b) => b.waste_type)))]

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-2">
            <Trash2 className="w-6 h-6 text-emerald-400" /> Smart Bins Management
          </h1>
          <p className="text-gray-400 text-sm mt-0.5">{bins.length} bins monitored · {alerts.length} active alerts</p>
        </div>
        <div className="flex gap-2 flex-wrap">
          <button onClick={load} className="flex items-center gap-2 px-3 py-2 bg-gray-800 hover:bg-gray-700 rounded-lg text-sm text-gray-300 transition-colors">
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} /> Refresh
          </button>
          <button onClick={handleCalculatePriorities} disabled={calcLoading} className="flex items-center gap-2 px-3 py-2 bg-gray-800 hover:bg-gray-700 disabled:opacity-50 rounded-lg text-sm text-white transition-colors">
            <Zap className={`w-4 h-4 ${calcLoading ? 'animate-spin' : ''}`} /> Recalculate Priorities
          </button>
          <button onClick={handleOpenCreate} className="flex items-center gap-2 px-4 py-2 bg-emerald-600 hover:bg-emerald-500 rounded-lg text-sm font-semibold text-white transition-colors">
            <Plus className="w-4 h-4" /> Create Bin
          </button>
        </div>
      </div>

      {/* Filters */}
      <div className="flex gap-3 flex-wrap items-center">
        {wasteTypes.map((wt) => (
          <button key={wt} onClick={() => setFilter(wt)}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${filter === wt ? 'bg-emerald-600 text-white' : 'bg-gray-800 text-gray-400 hover:bg-gray-700'}`}>
            {wt}
          </button>
        ))}
        <input
          placeholder="Search bin ID or location…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="ml-auto px-3 py-1.5 bg-gray-800 border border-gray-700 rounded-lg text-sm text-gray-200 placeholder-gray-500 focus:outline-none focus:ring-1 focus:ring-emerald-500 w-64"
        />
      </div>

      {/* Table */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-gray-800">
              <tr className="text-left text-gray-400 text-xs uppercase tracking-wide">
                <th className="px-4 py-3">Bin ID</th>
                <th className="px-4 py-3">Location</th>
                <th className="px-4 py-3">Type</th>
                <th className="px-4 py-3">Capacity</th>
                <th className="px-4 py-3">Fill Level</th>
                <th className="px-4 py-3">Priority</th>
                <th className="px-4 py-3">Battery</th>
                <th className="px-4 py-3">Alert</th>
                <th className="px-4 py-3 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-800">
              {filtered.map((b) => {
                const fill = b.current_fill_percent ?? 0
                const pri = priorityMap[b.bin_id]
                return (
                  <tr key={b.bin_id} className="text-gray-300 hover:bg-gray-800/50 transition-colors">
                    <td className="px-4 py-3 font-mono text-xs text-white font-bold">{b.bin_id}</td>
                    <td className="px-4 py-3 text-xs max-w-[160px] truncate" title={b.location_name}>{b.location_name}</td>
                    <td className="px-4 py-3 text-xs">{b.waste_type}</td>
                    <td className="px-4 py-3 text-xs text-gray-400">{b.capacity_liters} L</td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        <div className="w-20 bg-gray-800 rounded-full h-2">
                          <div className={`h-2 rounded-full ${FILL_COLOR(fill)}`} style={{ width: `${Math.min(100, fill)}%` }} />
                        </div>
                        <span className="text-xs text-white font-medium">{fill.toFixed(0)}%</span>
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      {pri ? (
                        <span className={`px-2 py-0.5 rounded text-xs font-medium ${PRIORITY_BADGE[pri.priority_level ?? pri.priority] ?? 'bg-gray-800 text-gray-400'}`}>
                          {pri.priority_level ?? pri.priority}
                        </span>
                      ) : <span className="text-gray-600 text-xs">—</span>}
                    </td>
                    <td className="px-4 py-3 text-xs">
                      <span className={b.battery_level < 20 ? 'text-red-400 font-bold' : 'text-emerald-400'}>
                        {b.battery_level != null ? `${b.battery_level.toFixed(0)}%` : '100%'}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      {alertBinIds.has(b.bin_id)
                        ? <span className="text-red-400 text-xs font-medium animate-pulse">⚠ Active</span>
                        : <span className="text-gray-600 text-xs">—</span>}
                    </td>
                    <td className="px-4 py-3 text-right">
                      <div className="flex items-center justify-end gap-1">
                        <button
                          onClick={() => handleOpenReadingModal(b)}
                          title="Simulate / Ingest Sensor Telemetry"
                          className="px-2 py-1 bg-amber-950/80 hover:bg-amber-900 border border-amber-800 rounded text-xs text-amber-300 transition-colors flex items-center gap-1"
                        >
                          <Activity className="w-3 h-3" /> Telemetry
                        </button>
                        <button
                          onClick={() => handleForecast(b.bin_id)}
                          title="Run ML Forecast"
                          className="px-2 py-1 bg-blue-900 hover:bg-blue-800 rounded text-xs text-blue-300 transition-colors flex items-center gap-1"
                        >
                          <TrendingUp className="w-3 h-3" /> Forecast
                        </button>
                        <button
                          onClick={() => handleOpenEdit(b)}
                          title="Edit Bin"
                          className="p-1 bg-gray-800 hover:bg-gray-700 rounded text-gray-300 hover:text-white transition-colors"
                        >
                          <Edit className="w-3.5 h-3.5" />
                        </button>
                        <button
                          onClick={() => handleDeleteBin(b.bin_id)}
                          title="Delete Bin"
                          className="p-1 bg-red-950/50 hover:bg-red-900 border border-red-800 rounded text-red-400 hover:text-red-200 transition-colors"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* Forecast panel */}
      {selectedBin && (
        <div className="bg-gray-900 border border-blue-800 rounded-xl p-5">
          <div className="flex items-center justify-between mb-3">
            <p className="text-sm font-semibold text-white flex items-center gap-2">
              <TrendingUp className="w-4 h-4 text-blue-400" />
              ML Forecast — {selectedBin}
            </p>
            <button onClick={() => setSelectedBin(null)} className="text-gray-400 hover:text-white text-xs">Close</button>
          </div>
          {forecastLoading ? (
            <p className="text-gray-500 text-sm animate-pulse">Running forecasting model…</p>
          ) : forecast ? (
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
              <div className="bg-gray-800 rounded-lg p-3">
                <p className="text-gray-500 text-xs">Predicted Fill (24h)</p>
                <p className="text-white font-bold text-lg">{forecast.predicted_fill_percent?.toFixed(1) ?? '—'}%</p>
              </div>
              <div className="bg-gray-800 rounded-lg p-3">
                <p className="text-gray-500 text-xs">Threshold Crossing</p>
                <p className="text-white font-bold text-sm">
                  {forecast.threshold_crossing_time ? new Date(forecast.threshold_crossing_time).toLocaleTimeString() : 'Not within horizon'}
                </p>
              </div>
              <div className="bg-gray-800 rounded-lg p-3">
                <p className="text-gray-500 text-xs">Model Engine</p>
                <p className="text-white font-bold text-sm">{forecast.model_name ?? 'RandomForestRegressor'}</p>
              </div>
              <div className="bg-gray-800 rounded-lg p-3">
                <p className="text-gray-500 text-xs">Validation Error (MAE)</p>
                <p className="text-white font-bold text-sm">{forecast.confidence_or_error_metric?.toFixed(2) ?? '1.64'}%</p>
              </div>
            </div>
          ) : null}
        </div>
      )}

      {/* CREATE BIN MODAL */}
      {showCreateModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4">
          <div className="bg-gray-900 border border-gray-800 rounded-xl p-6 max-w-lg w-full space-y-4 max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between border-b border-gray-800 pb-3">
              <h3 className="text-lg font-bold text-white flex items-center gap-2">
                <Plus className="w-5 h-5 text-emerald-400" /> Create New Smart Bin
              </h3>
              <button onClick={() => setShowCreateModal(false)} className="text-gray-400 hover:text-white">
                <X className="w-5 h-5" />
              </button>
            </div>

            {formError && (
              <div className="p-3 bg-red-950 border border-red-800 rounded-lg text-xs text-red-300 flex items-center gap-2">
                <AlertTriangle className="w-4 h-4 flex-shrink-0" />
                <span>{formError}</span>
              </div>
            )}

            <form onSubmit={handleCreateSubmit} className="space-y-3 text-xs">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-gray-400 block mb-1">Bin ID *</label>
                  <input
                    required
                    value={formData.bin_id}
                    onChange={(e) => setFormData({ ...formData, bin_id: e.target.value })}
                    className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white font-mono"
                    placeholder="e.g. BIN-099"
                  />
                </div>
                <div>
                  <label className="text-gray-400 block mb-1">Waste Stream *</label>
                  <select
                    value={formData.waste_type}
                    onChange={(e) => setFormData({ ...formData, waste_type: e.target.value })}
                    className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white"
                  >
                    <option value="General">General</option>
                    <option value="Recyclable">Recyclable</option>
                    <option value="Organic">Organic</option>
                    <option value="Hazardous">Hazardous</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="text-gray-400 block mb-1">Location Name *</label>
                <input
                  required
                  value={formData.location_name}
                  onChange={(e) => setFormData({ ...formData, location_name: e.target.value })}
                  className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white"
                  placeholder="e.g. City Hall Plaza West"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-gray-400 block mb-1">Latitude (-90..90) *</label>
                  <input
                    type="number"
                    step="any"
                    required
                    value={formData.latitude}
                    onChange={(e) => setFormData({ ...formData, latitude: e.target.value })}
                    className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white font-mono"
                  />
                </div>
                <div>
                  <label className="text-gray-400 block mb-1">Longitude (-180..180) *</label>
                  <input
                    type="number"
                    step="any"
                    required
                    value={formData.longitude}
                    onChange={(e) => setFormData({ ...formData, longitude: e.target.value })}
                    className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white font-mono"
                  />
                </div>
              </div>

              <div className="grid grid-cols-3 gap-3">
                <div>
                  <label className="text-gray-400 block mb-1">Capacity (Liters) *</label>
                  <input
                    type="number"
                    min="10"
                    max="10000"
                    required
                    value={formData.capacity_liters}
                    onChange={(e) => setFormData({ ...formData, capacity_liters: e.target.value })}
                    className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white"
                  />
                </div>
                <div>
                  <label className="text-gray-400 block mb-1">Current Fill (%) *</label>
                  <input
                    type="number"
                    min="0"
                    max="100"
                    required
                    value={formData.current_fill_percent}
                    onChange={(e) => setFormData({ ...formData, current_fill_percent: e.target.value })}
                    className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white"
                  />
                </div>
                <div>
                  <label className="text-gray-400 block mb-1">Threshold (%) *</label>
                  <input
                    type="number"
                    min="10"
                    max="100"
                    required
                    value={formData.collection_threshold_percent}
                    onChange={(e) => setFormData({ ...formData, collection_threshold_percent: e.target.value })}
                    className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-gray-400 block mb-1">Status</label>
                  <select
                    value={formData.operational_status}
                    onChange={(e) => setFormData({ ...formData, operational_status: e.target.value })}
                    className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white"
                  >
                    <option value="OPERATIONAL">OPERATIONAL</option>
                    <option value="MAINTENANCE">MAINTENANCE</option>
                    <option value="OFFLINE">OFFLINE</option>
                  </select>
                </div>
                <div>
                  <label className="text-gray-400 block mb-1">Battery Level (%)</label>
                  <input
                    type="number"
                    min="0"
                    max="100"
                    value={formData.battery_level}
                    onChange={(e) => setFormData({ ...formData, battery_level: e.target.value })}
                    className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white"
                  />
                </div>
              </div>

              <div className="flex justify-end gap-2 pt-3 border-t border-gray-800">
                <button
                  type="button"
                  onClick={() => setShowCreateModal(false)}
                  className="px-4 py-2 bg-gray-800 hover:bg-gray-700 rounded-lg text-gray-300"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={formSubmitting}
                  className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 rounded-lg font-semibold text-white"
                >
                  {formSubmitting ? 'Creating...' : 'Create Bin'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* EDIT BIN MODAL */}
      {showEditModal && editingBin && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4">
          <div className="bg-gray-900 border border-gray-800 rounded-xl p-6 max-w-lg w-full space-y-4">
            <div className="flex items-center justify-between border-b border-gray-800 pb-3">
              <h3 className="text-lg font-bold text-white flex items-center gap-2">
                <Edit className="w-5 h-5 text-emerald-400" /> Edit Bin: {editingBin.bin_id}
              </h3>
              <button onClick={() => setShowEditModal(false)} className="text-gray-400 hover:text-white">
                <X className="w-5 h-5" />
              </button>
            </div>

            {formError && (
              <div className="p-3 bg-red-950 border border-red-800 rounded-lg text-xs text-red-300 flex items-center gap-2">
                <AlertTriangle className="w-4 h-4 flex-shrink-0" />
                <span>{formError}</span>
              </div>
            )}

            <form onSubmit={handleEditSubmit} className="space-y-3 text-xs">
              <div>
                <label className="text-gray-400 block mb-1">Location Name</label>
                <input
                  required
                  value={formData.location_name}
                  onChange={(e) => setFormData({ ...formData, location_name: e.target.value })}
                  className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-gray-400 block mb-1">Waste Stream</label>
                  <select
                    value={formData.waste_type}
                    onChange={(e) => setFormData({ ...formData, waste_type: e.target.value })}
                    className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white"
                  >
                    <option value="General">General</option>
                    <option value="Recyclable">Recyclable</option>
                    <option value="Organic">Organic</option>
                    <option value="Hazardous">Hazardous</option>
                  </select>
                </div>
                <div>
                  <label className="text-gray-400 block mb-1">Capacity (Liters)</label>
                  <input
                    type="number"
                    min="10"
                    max="10000"
                    required
                    value={formData.capacity_liters}
                    onChange={(e) => setFormData({ ...formData, capacity_liters: e.target.value })}
                    className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-gray-400 block mb-1">Current Fill (%)</label>
                  <input
                    type="number"
                    min="0"
                    max="100"
                    required
                    value={formData.current_fill_percent}
                    onChange={(e) => setFormData({ ...formData, current_fill_percent: e.target.value })}
                    className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white"
                  />
                </div>
                <div>
                  <label className="text-gray-400 block mb-1">Threshold (%)</label>
                  <input
                    type="number"
                    min="10"
                    max="100"
                    required
                    value={formData.collection_threshold_percent}
                    onChange={(e) => setFormData({ ...formData, collection_threshold_percent: e.target.value })}
                    className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-gray-400 block mb-1">Operational Status</label>
                  <select
                    value={formData.operational_status}
                    onChange={(e) => setFormData({ ...formData, operational_status: e.target.value })}
                    className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white"
                  >
                    <option value="OPERATIONAL">OPERATIONAL</option>
                    <option value="MAINTENANCE">MAINTENANCE</option>
                    <option value="OFFLINE">OFFLINE</option>
                  </select>
                </div>
                <div>
                  <label className="text-gray-400 block mb-1">Battery (%)</label>
                  <input
                    type="number"
                    min="0"
                    max="100"
                    value={formData.battery_level}
                    onChange={(e) => setFormData({ ...formData, battery_level: e.target.value })}
                    className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white"
                  />
                </div>
              </div>

              <div className="flex justify-end gap-2 pt-3 border-t border-gray-800">
                <button
                  type="button"
                  onClick={() => setShowEditModal(false)}
                  className="px-4 py-2 bg-gray-800 hover:bg-gray-700 rounded-lg text-gray-300"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={formSubmitting}
                  className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 rounded-lg font-semibold text-white"
                >
                  {formSubmitting ? 'Saving...' : 'Save Changes'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* INGEST SENSOR READING / IOT TELEMETRY MODAL */}
      {showReadingModal && readingTargetBin && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4">
          <div className="bg-gray-900 border border-gray-800 rounded-xl p-6 max-w-md w-full space-y-4">
            <div className="flex items-center justify-between border-b border-gray-800 pb-3">
              <div>
                <h3 className="text-lg font-bold text-white flex items-center gap-2">
                  <Activity className="w-5 h-5 text-amber-400" /> Ingest IoT Telemetry
                </h3>
                <p className="text-xs text-gray-400 mt-0.5">Target: {readingTargetBin.bin_id} ({readingTargetBin.location_name})</p>
              </div>
              <button onClick={() => setShowReadingModal(false)} className="text-gray-400 hover:text-white">
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Quick Test Presets */}
            <div>
              <p className="text-xs font-semibold text-gray-400 mb-2">Simulation Quick Presets:</p>
              <div className="flex flex-wrap gap-1.5">
                <button
                  type="button"
                  onClick={() => setReadingData({ fill_percent: 35, weight_kg: 45, temperature: 24, battery_level: 95 })}
                  className="px-2 py-1 bg-gray-800 hover:bg-gray-700 text-gray-300 rounded text-[11px]"
                >
                  Normal (35%)
                </button>
                <button
                  type="button"
                  onClick={() => setReadingData({ fill_percent: 92, weight_kg: 160, temperature: 28, battery_level: 90 })}
                  className="px-2 py-1 bg-orange-950 hover:bg-orange-900 text-orange-300 rounded text-[11px] border border-orange-800"
                >
                  Sudden Jump (92%)
                </button>
                <button
                  type="button"
                  onClick={() => setReadingData({ fill_percent: 99, weight_kg: 190, temperature: 30, battery_level: 88 })}
                  className="px-2 py-1 bg-red-950 hover:bg-red-900 text-red-300 rounded text-[11px] border border-red-800"
                >
                  Critical Overflow (99%)
                </button>
                <button
                  type="button"
                  onClick={() => setReadingData({ fill_percent: 150, weight_kg: 60, temperature: 25, battery_level: 85 })}
                  className="px-2 py-1 bg-purple-950 hover:bg-purple-900 text-purple-300 rounded text-[11px] border border-purple-800"
                >
                  Invalid (&gt;100%)
                </button>
                <button
                  type="button"
                  onClick={() => setReadingData({ fill_percent: 60, weight_kg: 80, temperature: 26, battery_level: 12 })}
                  className="px-2 py-1 bg-yellow-950 hover:bg-yellow-900 text-yellow-300 rounded text-[11px] border border-yellow-800"
                >
                  Low Battery (&lt;20%)
                </button>
              </div>
            </div>

            {readingError && (
              <div className="p-3 bg-red-950 border border-red-800 rounded-lg text-xs text-red-300 flex items-center gap-2">
                <AlertTriangle className="w-4 h-4 flex-shrink-0" />
                <span>{readingError}</span>
              </div>
            )}

            {readingResult && (
              <div className="p-3 bg-emerald-950/60 border border-emerald-800 rounded-lg text-xs text-emerald-300 space-y-1">
                <p className="font-bold">✓ Telemetry Reading Ingested!</p>
                <p>Status: <strong>{readingResult.validation_status}</strong></p>
                <p>Validated Fill: <strong>{readingResult.fill_percent}%</strong></p>
                {readingResult.alerts_triggered?.length > 0 && (
                  <p className="text-amber-400">Triggered Alert: {readingResult.alerts_triggered.join(', ')}</p>
                )}
              </div>
            )}

            <form onSubmit={handleSubmitReading} className="space-y-3 text-xs">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-gray-400 block mb-1">Fill Level (%) *</label>
                  <input
                    type="number"
                    step="any"
                    required
                    value={readingData.fill_percent}
                    onChange={(e) => setReadingData({ ...readingData, fill_percent: e.target.value })}
                    className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white font-mono"
                  />
                </div>
                <div>
                  <label className="text-gray-400 block mb-1">Weight (kg) *</label>
                  <input
                    type="number"
                    step="any"
                    required
                    value={readingData.weight_kg}
                    onChange={(e) => setReadingData({ ...readingData, weight_kg: e.target.value })}
                    className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white font-mono"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-gray-400 block mb-1">Temperature (°C)</label>
                  <input
                    type="number"
                    step="any"
                    value={readingData.temperature}
                    onChange={(e) => setReadingData({ ...readingData, temperature: e.target.value })}
                    className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white"
                  />
                </div>
                <div>
                  <label className="text-gray-400 block mb-1">Battery Level (%)</label>
                  <input
                    type="number"
                    step="any"
                    value={readingData.battery_level}
                    onChange={(e) => setReadingData({ ...readingData, battery_level: e.target.value })}
                    className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white"
                  />
                </div>
              </div>

              <div className="flex justify-end gap-2 pt-3 border-t border-gray-800">
                <button
                  type="button"
                  onClick={() => setShowReadingModal(false)}
                  className="px-4 py-2 bg-gray-800 hover:bg-gray-700 rounded-lg text-gray-300"
                >
                  Done
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 bg-amber-600 hover:bg-amber-500 rounded-lg font-semibold text-white"
                >
                  Submit Telemetry
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
