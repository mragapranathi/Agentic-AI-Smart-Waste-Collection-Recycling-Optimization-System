import { useEffect, useState, useCallback } from 'react'
import { getVehicles, createVehicle, updateVehicle, deleteVehicle } from '../api/endpoints'
import { Truck, RefreshCw, Plus, Edit, Trash2, X, AlertTriangle } from 'lucide-react'

const STATUS_COLORS: Record<string, string> = {
  AVAILABLE: 'bg-emerald-900 text-emerald-300',
  ASSIGNED: 'bg-blue-900 text-blue-300',
  IN_TRANSIT: 'bg-amber-900 text-amber-300',
  COLLECTING: 'bg-cyan-900 text-cyan-300',
  MAINTENANCE: 'bg-red-900 text-red-300',
  OFFLINE: 'bg-gray-800 text-gray-400',
}

const ALL_WASTE_TYPES = ['General', 'Recyclable', 'Organic', 'Hazardous']

export default function VehiclesPage() {
  const [vehicles, setVehicles] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [statusFilter, setStatusFilter] = useState('ALL')

  // Modals state
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [showEditModal, setShowEditModal] = useState(false)
  const [editingVehicle, setEditingVehicle] = useState<any | null>(null)

  // Form state
  const [formData, setFormData] = useState<Record<string, any>>({
    vehicle_id: '',
    vehicle_type: 'Compactor Truck',
    capacity_liters: 8000,
    supported_waste_types: ['General'],
    current_load_liters: 0,
    status: 'AVAILABLE',
    latitude: 12.9716,
    longitude: 77.5946,
  })
  const [formError, setFormError] = useState<string | null>(null)
  const [formSubmitting, setFormSubmitting] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const v = await getVehicles()
      setVehicles(v)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load() }, [load])

  const handleOpenCreate = () => {
    setFormData({
      vehicle_id: `TRUCK-MUNI-${Math.floor(10 + Math.random() * 90)}`,
      vehicle_type: 'Compactor Truck',
      capacity_liters: 8000,
      supported_waste_types: ['General'],
      current_load_liters: 0,
      status: 'AVAILABLE',
      latitude: 12.9716,
      longitude: 77.5946,
    })
    setFormError(null)
    setShowCreateModal(true)
  }

  const handleOpenEdit = (v: any) => {
    setEditingVehicle(v)
    setFormData({
      vehicle_type: v.vehicle_type || 'Compactor Truck',
      capacity_liters: v.capacity_liters,
      supported_waste_types: v.supported_waste_types || ['General'],
      current_load_liters: v.current_load_liters ?? 0,
      status: v.status,
      latitude: v.latitude ?? 12.9716,
      longitude: v.longitude ?? 77.5946,
    })
    setFormError(null)
    setShowEditModal(true)
  }

  const handleToggleWasteType = (wt: string) => {
    const current = formData.supported_waste_types || []
    if (current.includes(wt)) {
      if (current.length === 1) return // Keep at least one
      setFormData({ ...formData, supported_waste_types: current.filter((x: string) => x !== wt) })
    } else {
      setFormData({ ...formData, supported_waste_types: [...current, wt] })
    }
  }

  const handleCreateSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setFormError(null)

    if (!formData.vehicle_id || !formData.vehicle_id.trim()) {
      setFormError('Vehicle ID is required.')
      return
    }
    if (formData.capacity_liters <= 0) {
      setFormError('Capacity must be greater than 0 Liters.')
      return
    }
    if (formData.current_load_liters < 0 || formData.current_load_liters > formData.capacity_liters) {
      setFormError('Current load cannot be negative or exceed total vehicle capacity.')
      return
    }
    if (!formData.supported_waste_types || formData.supported_waste_types.length === 0) {
      setFormError('Select at least one supported waste type.')
      return
    }

    setFormSubmitting(true)
    try {
      await createVehicle({
        ...formData,
        capacity_liters: Number(formData.capacity_liters),
        current_load_liters: Number(formData.current_load_liters),
        latitude: Number(formData.latitude),
        longitude: Number(formData.longitude),
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
    if (!editingVehicle) return
    setFormError(null)

    if (formData.capacity_liters <= 0) {
      setFormError('Capacity must be greater than 0 Liters.')
      return
    }
    if (formData.current_load_liters < 0 || formData.current_load_liters > formData.capacity_liters) {
      setFormError('Current load cannot be negative or exceed total vehicle capacity.')
      return
    }

    setFormSubmitting(true)
    try {
      await updateVehicle(editingVehicle.vehicle_id, {
        vehicle_type: formData.vehicle_type,
        capacity_liters: Number(formData.capacity_liters),
        supported_waste_types: formData.supported_waste_types,
        current_load_liters: Number(formData.current_load_liters),
        status: formData.status,
        latitude: Number(formData.latitude),
        longitude: Number(formData.longitude),
      })
      setShowEditModal(false)
      await load()
    } catch (err: any) {
      setFormError(err.response?.data?.detail || err.message)
    } finally {
      setFormSubmitting(false)
    }
  }

  const handleDeleteVehicle = async (vehicleId: string) => {
    if (!window.confirm(`Are you sure you want to remove Vehicle ${vehicleId} from active registry?`)) return
    try {
      await deleteVehicle(vehicleId)
      await load()
    } catch (err: any) {
      alert(`Failed to delete vehicle: ${err.response?.data?.detail || err.message}`)
    }
  }

  const statuses = ['ALL', ...Array.from(new Set(vehicles.map((v) => v.status)))]
  const filtered = statusFilter === 'ALL' ? vehicles : vehicles.filter((v) => v.status === statusFilter)

  const counts = vehicles.reduce((acc: Record<string, number>, v) => {
    acc[v.status] = (acc[v.status] ?? 0) + 1
    return acc
  }, {})

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-2">
            <Truck className="w-6 h-6 text-emerald-400" /> Fleet Management
          </h1>
          <p className="text-gray-400 text-sm mt-0.5">{vehicles.length} vehicles in active fleet registry</p>
        </div>
        <div className="flex gap-2">
          <button onClick={load} className="flex items-center gap-2 px-3 py-2 bg-gray-800 hover:bg-gray-700 rounded-lg text-sm text-gray-300 transition-colors">
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} /> Refresh
          </button>
          <button onClick={handleOpenCreate} className="flex items-center gap-2 px-4 py-2 bg-emerald-600 hover:bg-emerald-500 rounded-lg text-sm font-semibold text-white transition-colors">
            <Plus className="w-4 h-4" /> Add Vehicle
          </button>
        </div>
      </div>

      {/* Status summary cards */}
      <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-6 gap-3">
        {Object.entries(counts).map(([status, count]) => (
          <div key={status} className="bg-gray-900 border border-gray-800 rounded-lg p-3 text-center">
            <p className="text-xl font-bold text-white">{count}</p>
            <span className={`text-xs px-2 py-0.5 rounded font-medium ${STATUS_COLORS[status] ?? 'bg-gray-800 text-gray-400'}`}>{status}</span>
          </div>
        ))}
      </div>

      {/* Filter */}
      <div className="flex gap-2 flex-wrap">
        {statuses.map((s) => (
          <button key={s} onClick={() => setStatusFilter(s)}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${statusFilter === s ? 'bg-emerald-600 text-white' : 'bg-gray-800 text-gray-400 hover:bg-gray-700'}`}>
            {s}
          </button>
        ))}
      </div>

      {/* Table */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-gray-800">
              <tr className="text-left text-gray-400 text-xs uppercase tracking-wide">
                <th className="px-4 py-3">Vehicle ID</th>
                <th className="px-4 py-3">Status</th>
                <th className="px-4 py-3">Type</th>
                <th className="px-4 py-3">Supported Waste Streams</th>
                <th className="px-4 py-3">Capacity</th>
                <th className="px-4 py-3">Load / Utilization</th>
                <th className="px-4 py-3 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-800">
              {filtered.map((v) => {
                const util = Math.min(100, ((v.current_load_liters ?? 0) / (v.capacity_liters ?? 1)) * 100)
                return (
                  <tr key={v.vehicle_id} className="text-gray-300 hover:bg-gray-800/50 transition-colors">
                    <td className="px-4 py-3 font-mono text-xs text-white font-bold">{v.vehicle_id}</td>
                    <td className="px-4 py-3">
                      <span className={`px-2 py-0.5 rounded text-xs font-medium ${STATUS_COLORS[v.status] ?? 'bg-gray-800 text-gray-400'}`}>
                        {v.status}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-xs text-gray-300">{v.vehicle_type || 'Compactor Truck'}</td>
                    <td className="px-4 py-3 text-xs">
                      <div className="flex gap-1 flex-wrap">
                        {(v.supported_waste_types ?? []).map((wt: string) => (
                          <span key={wt} className="px-1.5 py-0.5 bg-gray-800 text-gray-300 rounded text-[11px] border border-gray-700">
                            {wt}
                          </span>
                        ))}
                      </div>
                    </td>
                    <td className="px-4 py-3 text-xs">{v.capacity_liters?.toFixed(0)} L</td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        <div className="w-24 bg-gray-800 rounded-full h-2">
                          <div
                            className={`h-2 rounded-full ${util >= 85 ? 'bg-red-500' : util >= 50 ? 'bg-amber-500' : 'bg-emerald-500'}`}
                            style={{ width: `${util}%` }}
                          />
                        </div>
                        <span className="text-xs text-gray-300 font-mono">{v.current_load_liters ?? 0}L ({util.toFixed(0)}%)</span>
                      </div>
                    </td>
                    <td className="px-4 py-3 text-right">
                      <div className="flex items-center justify-end gap-1.5">
                        <button
                          onClick={() => handleOpenEdit(v)}
                          title="Edit Vehicle"
                          className="p-1 bg-gray-800 hover:bg-gray-700 rounded text-gray-300 hover:text-white transition-colors"
                        >
                          <Edit className="w-3.5 h-3.5" />
                        </button>
                        <button
                          onClick={() => handleDeleteVehicle(v.vehicle_id)}
                          title="Delete / Deactivate Vehicle"
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

      {/* CREATE VEHICLE MODAL */}
      {showCreateModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4">
          <div className="bg-gray-900 border border-gray-800 rounded-xl p-6 max-w-lg w-full space-y-4">
            <div className="flex items-center justify-between border-b border-gray-800 pb-3">
              <h3 className="text-lg font-bold text-white flex items-center gap-2">
                <Plus className="w-5 h-5 text-emerald-400" /> Register Fleet Vehicle
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
                  <label className="text-gray-400 block mb-1">Vehicle ID *</label>
                  <input
                    required
                    value={formData.vehicle_id}
                    onChange={(e) => setFormData({ ...formData, vehicle_id: e.target.value })}
                    className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white font-mono"
                    placeholder="e.g. TRUCK-05"
                  />
                </div>
                <div>
                  <label className="text-gray-400 block mb-1">Vehicle Type *</label>
                  <select
                    value={formData.vehicle_type}
                    onChange={(e) => setFormData({ ...formData, vehicle_type: e.target.value })}
                    className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white"
                  >
                    <option value="Compactor Truck">Compactor Truck</option>
                    <option value="Recycling Side-Loader">Recycling Side-Loader</option>
                    <option value="Electric Collection Van">Electric Collection Van</option>
                    <option value="Heavy Bio-Waste Tipper">Heavy Bio-Waste Tipper</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="text-gray-400 block mb-1.5">Supported Waste Streams *</label>
                <div className="flex gap-2 flex-wrap">
                  {ALL_WASTE_TYPES.map((wt) => {
                    const selected = (formData.supported_waste_types || []).includes(wt)
                    return (
                      <button
                        type="button"
                        key={wt}
                        onClick={() => handleToggleWasteType(wt)}
                        className={`px-3 py-1.5 rounded-lg border text-xs font-medium transition-colors ${
                          selected
                            ? 'bg-emerald-950 text-emerald-300 border-emerald-600'
                            : 'bg-gray-800 text-gray-400 border-gray-700 hover:bg-gray-700'
                        }`}
                      >
                        {wt}
                      </button>
                    )
                  })}
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-gray-400 block mb-1">Total Capacity (Liters) *</label>
                  <input
                    type="number"
                    min="500"
                    max="50000"
                    required
                    value={formData.capacity_liters}
                    onChange={(e) => setFormData({ ...formData, capacity_liters: e.target.value })}
                    className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white font-mono"
                  />
                </div>
                <div>
                  <label className="text-gray-400 block mb-1">Current Load (Liters)</label>
                  <input
                    type="number"
                    min="0"
                    value={formData.current_load_liters}
                    onChange={(e) => setFormData({ ...formData, current_load_liters: e.target.value })}
                    className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white font-mono"
                  />
                </div>
              </div>

              <div className="grid grid-cols-3 gap-3">
                <div>
                  <label className="text-gray-400 block mb-1">Status</label>
                  <select
                    value={formData.status}
                    onChange={(e) => setFormData({ ...formData, status: e.target.value })}
                    className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white"
                  >
                    <option value="AVAILABLE">AVAILABLE</option>
                    <option value="ASSIGNED">ASSIGNED</option>
                    <option value="IN_TRANSIT">IN_TRANSIT</option>
                    <option value="MAINTENANCE">MAINTENANCE</option>
                  </select>
                </div>
                <div>
                  <label className="text-gray-400 block mb-1">Latitude</label>
                  <input
                    type="number"
                    step="any"
                    value={formData.latitude}
                    onChange={(e) => setFormData({ ...formData, latitude: e.target.value })}
                    className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white font-mono"
                  />
                </div>
                <div>
                  <label className="text-gray-400 block mb-1">Longitude</label>
                  <input
                    type="number"
                    step="any"
                    value={formData.longitude}
                    onChange={(e) => setFormData({ ...formData, longitude: e.target.value })}
                    className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white font-mono"
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
                  {formSubmitting ? 'Registering...' : 'Register Vehicle'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* EDIT VEHICLE MODAL */}
      {showEditModal && editingVehicle && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4">
          <div className="bg-gray-900 border border-gray-800 rounded-xl p-6 max-w-lg w-full space-y-4">
            <div className="flex items-center justify-between border-b border-gray-800 pb-3">
              <h3 className="text-lg font-bold text-white flex items-center gap-2">
                <Edit className="w-5 h-5 text-emerald-400" /> Edit Vehicle: {editingVehicle.vehicle_id}
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
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-gray-400 block mb-1">Capacity (Liters)</label>
                  <input
                    type="number"
                    min="500"
                    max="50000"
                    required
                    value={formData.capacity_liters}
                    onChange={(e) => setFormData({ ...formData, capacity_liters: e.target.value })}
                    className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white font-mono"
                  />
                </div>
                <div>
                  <label className="text-gray-400 block mb-1">Current Load (Liters)</label>
                  <input
                    type="number"
                    min="0"
                    required
                    value={formData.current_load_liters}
                    onChange={(e) => setFormData({ ...formData, current_load_liters: e.target.value })}
                    className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white font-mono"
                  />
                </div>
              </div>

              <div>
                <label className="text-gray-400 block mb-1.5">Supported Waste Streams</label>
                <div className="flex gap-2 flex-wrap">
                  {ALL_WASTE_TYPES.map((wt) => {
                    const selected = (formData.supported_waste_types || []).includes(wt)
                    return (
                      <button
                        type="button"
                        key={wt}
                        onClick={() => handleToggleWasteType(wt)}
                        className={`px-3 py-1.5 rounded-lg border text-xs font-medium transition-colors ${
                          selected
                            ? 'bg-emerald-950 text-emerald-300 border-emerald-600'
                            : 'bg-gray-800 text-gray-400 border-gray-700 hover:bg-gray-700'
                        }`}
                      >
                        {wt}
                      </button>
                    )
                  })}
                </div>
              </div>

              <div className="grid grid-cols-3 gap-3">
                <div>
                  <label className="text-gray-400 block mb-1">Status</label>
                  <select
                    value={formData.status}
                    onChange={(e) => setFormData({ ...formData, status: e.target.value })}
                    className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white"
                  >
                    <option value="AVAILABLE">AVAILABLE</option>
                    <option value="ASSIGNED">ASSIGNED</option>
                    <option value="IN_TRANSIT">IN_TRANSIT</option>
                    <option value="COLLECTING">COLLECTING</option>
                    <option value="MAINTENANCE">MAINTENANCE</option>
                    <option value="OFFLINE">OFFLINE</option>
                  </select>
                </div>
                <div>
                  <label className="text-gray-400 block mb-1">Latitude</label>
                  <input
                    type="number"
                    step="any"
                    value={formData.latitude}
                    onChange={(e) => setFormData({ ...formData, latitude: e.target.value })}
                    className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white font-mono"
                  />
                </div>
                <div>
                  <label className="text-gray-400 block mb-1">Longitude</label>
                  <input
                    type="number"
                    step="any"
                    value={formData.longitude}
                    onChange={(e) => setFormData({ ...formData, longitude: e.target.value })}
                    className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white font-mono"
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
    </div>
  )
}
