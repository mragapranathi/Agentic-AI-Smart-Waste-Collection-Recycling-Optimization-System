import { useEffect, useState, useCallback } from 'react'
import { getRoutes, optimizeRoutes, replanRoute, getBins, getVehicles } from '../api/endpoints'
import { Navigation, RefreshCw, Zap, ShieldCheck, AlertCircle, Play, Layers, CheckSquare, Square, AlertTriangle } from 'lucide-react'
import RouteMap from '../components/RouteMap'

export default function RoutesPage() {
  const [routes, setRoutes] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [optimizing, setOptimizing] = useState(false)
  const [selectedRoute, setSelectedRoute] = useState<any | null>(null)

  // Dynamic Replanning state
  const [replanBinId, setReplanBinId] = useState('')
  const [replanReason, setReplanReason] = useState('Critical overflow alert triggered')
  const [replanning, setReplanning] = useState(false)
  const [replanResult, setReplanResult] = useState<any | null>(null)
  const [replanError, setReplanError] = useState<string | null>(null)

  // Custom Interactive Planner state
  const [availableBins, setAvailableBins] = useState<any[]>([])
  const [availableVehicles, setAvailableVehicles] = useState<any[]>([])
  const [selectedBinIds, setSelectedBinIds] = useState<string[]>([])
  const [selectedVehicleIds, setSelectedVehicleIds] = useState<string[]>([])
  const [depotLat, setDepotLat] = useState<number>(12.9716)
  const [depotLng, setDepotLng] = useState<number>(77.5946)
  const [plannerError, setPlannerError] = useState<string | null>(null)
  const [plannerSuccess, setPlannerSuccess] = useState<string | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const [r, b, v] = await Promise.all([
        getRoutes(),
        getBins(),
        getVehicles({ status: 'AVAILABLE' })
      ])
      setRoutes(r)
      setAvailableBins(b)
      setAvailableVehicles(v)
      if (r.length > 0 && !selectedRoute) {
        setSelectedRoute(r[0])
      } else if (selectedRoute) {
        const updated = r.find((x: any) => x.route_id === selectedRoute.route_id)
        if (updated) setSelectedRoute(updated)
      }
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }, [selectedRoute])

  useEffect(() => { load() }, [])

  // Auto-optimize all high priority bins
  const handleRunOptimizer = async () => {
    setOptimizing(true)
    setPlannerError(null)
    setPlannerSuccess(null)
    try {
      const res = await optimizeRoutes({ planning_period_hours: 24, save_to_db: true })
      await load()
      if (res.routes && res.routes.length > 0) {
        setSelectedRoute(res.routes[0])
        setPlannerSuccess(`Successfully generated and dispatched ${res.routes.length} route(s)!`)
      } else {
        setPlannerError('No routes generated. Check that high-priority bins exist and vehicles are available.')
      }
    } catch (e: any) {
      setPlannerError(e.response?.data?.detail || e.message)
    } finally {
      setOptimizing(false)
    }
  }

  // Interactive Custom Optimization
  const handleCustomOptimize = async () => {
    if (selectedBinIds.length === 0) {
      setPlannerError('Please select at least one bin for collection.')
      return
    }
    if (selectedVehicleIds.length === 0) {
      setPlannerError('Please select at least one available vehicle.')
      return
    }

    setOptimizing(true)
    setPlannerError(null)
    setPlannerSuccess(null)

    try {
      const res = await optimizeRoutes({
        bin_ids: selectedBinIds,
        vehicle_ids: selectedVehicleIds,
        depot_lat: Number(depotLat),
        depot_lng: Number(depotLng),
        save_to_db: true,
      })

      await load()
      if (res.routes && res.routes.length > 0) {
        setSelectedRoute(res.routes[0])
        setPlannerSuccess(`Optimized route generated with ${res.routes[0].stops?.length || 0} stops! Dispatched to fleet.`)
        setSelectedBinIds([])
      } else if (res.unassigned_bins && res.unassigned_bins.length > 0) {
        setPlannerError(`Route could not be formed: ${res.unassigned_bins[0].reason}`)
      }
    } catch (e: any) {
      setPlannerError(e.response?.data?.detail || e.message)
    } finally {
      setOptimizing(false)
    }
  }

  const handleToggleBin = (binId: string) => {
    setSelectedBinIds((prev) =>
      prev.includes(binId) ? prev.filter((id) => id !== binId) : [...prev, binId]
    )
  }

  const handleToggleVehicle = (vid: string) => {
    setSelectedVehicleIds((prev) =>
      prev.includes(vid) ? prev.filter((id) => id !== vid) : [...prev, vid]
    )
  }

  const handleSelectAllHighPriority = () => {
    const highBins = availableBins
      .filter((b) => (b.current_fill_percent ?? 0) >= (b.collection_threshold_percent ?? 80))
      .map((b) => b.bin_id)
    setSelectedBinIds(highBins)
  }

  const handleReplan = async () => {
    if (!selectedRoute || !replanBinId) return
    setReplanning(true)
    setReplanResult(null)
    setReplanError(null)
    try {
      const res = await replanRoute(selectedRoute.route_id, {
        trigger_bin_id: replanBinId,
        reason: replanReason,
      })
      setReplanResult(res)
      await load()
    } catch (e: any) {
      setReplanError(e.response?.data?.detail || e.message)
    } finally {
      setReplanning(false)
    }
  }

  // Live calculations for planner
  const selectedBinsObjects = availableBins.filter((b) => selectedBinIds.includes(b.bin_id))
  const selectedVehiclesObjects = availableVehicles.filter((v) => selectedVehicleIds.includes(v.vehicle_id))
  const totalDemand = selectedBinsObjects.reduce(
    (sum, b) => sum + (b.capacity_liters * (b.current_fill_percent / 100)),
    0
  )
  const totalCapacity = selectedVehiclesObjects.reduce(
    (sum, v) => sum + (v.capacity_liters - (v.current_load_liters ?? 0)),
    0
  )
  const capacityOverflow = totalDemand > totalCapacity && selectedVehiclesObjects.length > 0

  const stops = selectedRoute?.stops ?? []

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-2">
            <Navigation className="w-6 h-6 text-emerald-400" /> Route Optimization & Dispatch
          </h1>
          <p className="text-gray-400 text-sm mt-0.5">
            Google OR-Tools CVRP solver · Dynamic surge insertion · Interactive custom planning
          </p>
        </div>
        <div className="flex gap-2 flex-wrap">
          <button
            onClick={load}
            className="flex items-center gap-2 px-3 py-2 bg-gray-800 hover:bg-gray-700 rounded-lg text-sm text-gray-300 transition-colors"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} /> Refresh
          </button>
          <button
            onClick={handleRunOptimizer}
            disabled={optimizing}
            className="flex items-center gap-2 px-4 py-2 bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 rounded-lg text-sm font-semibold text-white transition-colors"
          >
            <Zap className={`w-4 h-4 ${optimizing ? 'animate-spin' : ''}`} />
            {optimizing ? 'Solving CVRP...' : 'Auto-Optimize High Priority Bins'}
          </button>
        </div>
      </div>

      {/* CUSTOM ROUTE OPTIMIZATION WIZARD */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-5 space-y-4">
        <div className="flex items-center justify-between border-b border-gray-800 pb-3 flex-wrap gap-2">
          <div className="flex items-center gap-2">
            <Layers className="w-5 h-5 text-emerald-400" />
            <h2 className="text-sm font-bold text-white uppercase tracking-wide">
              Interactive Custom Route Planner (OR-Tools)
            </h2>
          </div>
          <button
            onClick={handleSelectAllHighPriority}
            className="text-xs text-emerald-400 hover:text-emerald-300 font-semibold"
          >
            + Select All Urgent Bins (&ge; threshold)
          </button>
        </div>

        {plannerError && (
          <div className="p-3 bg-red-950/60 border border-red-800 rounded-lg text-xs text-red-300 flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 flex-shrink-0" />
            <span>{plannerError}</span>
          </div>
        )}

        {plannerSuccess && (
          <div className="p-3 bg-emerald-950/60 border border-emerald-800 rounded-lg text-xs text-emerald-300">
            ✓ {plannerSuccess}
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 text-xs">
          {/* Step 1: Select Bins */}
          <div className="bg-gray-800/60 border border-gray-700/60 rounded-xl p-3.5 space-y-2">
            <div className="flex items-center justify-between">
              <span className="font-bold text-white">1. Select Target Bins ({selectedBinIds.length})</span>
              <span className="text-[11px] text-gray-400">Demand: <strong>{totalDemand.toFixed(0)} L</strong></span>
            </div>
            <div className="max-h-48 overflow-y-auto space-y-1.5 pr-1">
              {availableBins.map((b) => {
                const isSelected = selectedBinIds.includes(b.bin_id)
                const isUrgent = (b.current_fill_percent ?? 0) >= (b.collection_threshold_percent ?? 80)
                return (
                  <div
                    key={b.bin_id}
                    onClick={() => handleToggleBin(b.bin_id)}
                    className={`flex items-center justify-between p-2 rounded-lg cursor-pointer border transition-colors ${
                      isSelected
                        ? 'bg-emerald-950/60 border-emerald-600 text-white'
                        : 'bg-gray-900/60 border-gray-800 text-gray-300 hover:bg-gray-800'
                    }`}
                  >
                    <div className="flex items-center gap-2 min-w-0">
                      {isSelected ? <CheckSquare className="w-4 h-4 text-emerald-400" /> : <Square className="w-4 h-4 text-gray-500" />}
                      <div className="truncate">
                        <span className="font-mono font-bold text-xs">{b.bin_id}</span>
                        <span className="text-[11px] text-gray-400 ml-1.5">{b.waste_type}</span>
                      </div>
                    </div>
                    <span className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${
                      isUrgent ? 'bg-red-950 text-red-300' : 'bg-gray-800 text-gray-400'
                    }`}>
                      {b.current_fill_percent?.toFixed(0)}%
                    </span>
                  </div>
                )
              })}
            </div>
          </div>

          {/* Step 2: Select Vehicle */}
          <div className="bg-gray-800/60 border border-gray-700/60 rounded-xl p-3.5 space-y-2">
            <div className="flex items-center justify-between">
              <span className="font-bold text-white">2. Select Vehicle ({selectedVehicleIds.length})</span>
              <span className={`text-[11px] font-bold ${capacityOverflow ? 'text-red-400' : 'text-emerald-400'}`}>
                Cap: {totalCapacity.toFixed(0)} L
              </span>
            </div>
            <div className="max-h-48 overflow-y-auto space-y-1.5 pr-1">
              {availableVehicles.map((v) => {
                const isSelected = selectedVehicleIds.includes(v.vehicle_id)
                return (
                  <div
                    key={v.vehicle_id}
                    onClick={() => handleToggleVehicle(v.vehicle_id)}
                    className={`flex items-center justify-between p-2 rounded-lg cursor-pointer border transition-colors ${
                      isSelected
                        ? 'bg-blue-950/60 border-blue-600 text-white'
                        : 'bg-gray-900/60 border-gray-800 text-gray-300 hover:bg-gray-800'
                    }`}
                  >
                    <div className="flex items-center gap-2 min-w-0">
                      {isSelected ? <CheckSquare className="w-4 h-4 text-blue-400" /> : <Square className="w-4 h-4 text-gray-500" />}
                      <div className="truncate">
                        <span className="font-mono font-bold text-xs">{v.vehicle_id}</span>
                        <span className="text-[11px] text-gray-400 ml-1.5">{(v.supported_waste_types || []).join(', ')}</span>
                      </div>
                    </div>
                    <span className="text-[11px] font-mono text-gray-300">{v.capacity_liters} L</span>
                  </div>
                )
              })}
            </div>
          </div>

          {/* Step 3: Depot & Dispatch */}
          <div className="bg-gray-800/60 border border-gray-700/60 rounded-xl p-3.5 space-y-3 flex flex-col justify-between">
            <div>
              <span className="font-bold text-white block mb-2">3. Municipal Depot Location</span>
              <div className="grid grid-cols-2 gap-2 mb-3">
                <div>
                  <label className="text-gray-400 text-[11px] block mb-0.5">Depot Lat</label>
                  <input
                    type="number"
                    step="any"
                    value={depotLat}
                    onChange={(e) => setDepotLat(Number(e.target.value))}
                    className="w-full bg-gray-900 border border-gray-700 rounded px-2 py-1 text-white font-mono text-xs"
                  />
                </div>
                <div>
                  <label className="text-gray-400 text-[11px] block mb-0.5">Depot Lng</label>
                  <input
                    type="number"
                    step="any"
                    value={depotLng}
                    onChange={(e) => setDepotLng(Number(e.target.value))}
                    className="w-full bg-gray-900 border border-gray-700 rounded px-2 py-1 text-white font-mono text-xs"
                  />
                </div>
              </div>

              {capacityOverflow && (
                <div className="p-2 bg-red-950 border border-red-800 rounded text-red-300 text-[11px]">
                  ⚠ Total demand ({totalDemand.toFixed(0)} L) exceeds selected capacity ({totalCapacity.toFixed(0)} L).
                </div>
              )}
            </div>

            <button
              onClick={handleCustomOptimize}
              disabled={optimizing || selectedBinIds.length === 0 || selectedVehicleIds.length === 0 || capacityOverflow}
              className="w-full py-2.5 bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 rounded-lg font-semibold text-white transition-colors flex items-center justify-center gap-2"
            >
              <Zap className={`w-4 h-4 ${optimizing ? 'animate-spin' : ''}`} />
              {optimizing ? 'Solving OR-Tools CVRP...' : 'Optimize & Dispatch Route'}
            </button>
          </div>
        </div>
      </div>

      {/* Main Grid: Routes List & Details */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left: Routes Directory */}
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-5 space-y-4">
          <div className="flex items-center justify-between">
            <span className="text-sm font-semibold text-white">Active Routes ({routes.length})</span>
            <span className="text-xs text-gray-500">Sorted by newest</span>
          </div>

          {routes.length === 0 ? (
            <div className="py-12 text-center text-gray-500 text-sm">
              <Navigation className="w-8 h-8 mx-auto mb-2 text-gray-600" />
              No routes planned yet.<br />
              Use the planner above to generate vehicle routes.
            </div>
          ) : (
            <div className="space-y-3 max-h-[620px] overflow-y-auto pr-1">
              {routes.map((r) => {
                const isSelected = selectedRoute?.route_id === r.route_id
                return (
                  <div
                    key={r.route_id}
                    onClick={() => setSelectedRoute(r)}
                    className={`p-4 rounded-xl border cursor-pointer transition-all ${
                      isSelected
                        ? 'border-emerald-500 bg-emerald-950/20'
                        : 'border-gray-800 bg-gray-800/40 hover:bg-gray-800 hover:border-gray-700'
                    }`}
                  >
                    <div className="flex items-center justify-between mb-2">
                      <span className="font-mono text-xs font-bold text-white">{r.route_id}</span>
                      <span className={`px-2 py-0.5 rounded text-[11px] font-semibold ${
                        r.route_status === 'APPROVED' ? 'bg-emerald-900 text-emerald-300' :
                        r.route_status === 'IN_PROGRESS' ? 'bg-blue-900 text-blue-300' :
                        r.route_status === 'COMPLETED' ? 'bg-purple-900 text-purple-300' :
                        'bg-amber-900 text-amber-300'
                      }`}>
                        {r.route_status}
                      </span>
                    </div>

                    <div className="grid grid-cols-2 gap-2 text-xs text-gray-400 mt-2">
                      <div>
                        <span className="text-gray-500 block">Vehicle</span>
                        <span className="text-gray-200 font-medium">{r.vehicle_id}</span>
                      </div>
                      <div>
                        <span className="text-gray-500 block">Stops</span>
                        <span className="text-gray-200 font-medium">{r.stops?.length ?? 0} bins</span>
                      </div>
                      <div>
                        <span className="text-gray-500 block">Distance</span>
                        <span className="text-gray-200 font-medium">{r.total_distance_km?.toFixed(1)} km</span>
                      </div>
                      <div>
                        <span className="text-gray-500 block">Est. Duration</span>
                        <span className="text-gray-200 font-medium">{r.estimated_duration_minutes?.toFixed(0)} min</span>
                      </div>
                    </div>
                  </div>
                )
              })}
            </div>
          )}
        </div>

        {/* Right 2 cols: Selected Route Details & Map */}
        <div className="lg:col-span-2 space-y-6">
          {selectedRoute ? (
            <>
              {/* Route Summary Banner */}
              <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
                <div className="flex items-center justify-between flex-wrap gap-4 border-b border-gray-800 pb-4 mb-4">
                  <div>
                    <div className="flex items-center gap-3">
                      <h2 className="text-lg font-bold text-white font-mono">{selectedRoute.route_id}</h2>
                      <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-900/60 text-emerald-300 border border-emerald-700">
                        {selectedRoute.route_status}
                      </span>
                    </div>
                    <p className="text-xs text-gray-400 mt-1">
                      Assigned Vehicle: <span className="text-emerald-400 font-semibold">{selectedRoute.vehicle_id}</span> ·
                      Optimization Score: <span className="text-gray-200 font-mono">{(selectedRoute.optimization_score ?? 1.0).toFixed(2)}</span>
                    </p>
                  </div>

                  <div className="flex gap-4 text-sm">
                    <div className="text-right">
                      <p className="text-xs text-gray-500 uppercase tracking-wide">Total Distance</p>
                      <p className="text-base font-bold text-white">{selectedRoute.total_distance_km?.toFixed(2)} km</p>
                    </div>
                    <div className="text-right">
                      <p className="text-xs text-gray-500 uppercase tracking-wide">Est. Duration</p>
                      <p className="text-base font-bold text-white">{selectedRoute.estimated_duration_minutes?.toFixed(0)} min</p>
                    </div>
                  </div>
                </div>

                {/* Map */}
                <div className="h-64 rounded-lg overflow-hidden border border-gray-800 mb-4">
                  <RouteMap stops={stops} />
                </div>

                {/* Stops Table */}
                <div>
                  <h3 className="text-sm font-semibold text-white mb-2">Ordered Stops Sequence</h3>
                  <div className="overflow-x-auto rounded-lg border border-gray-800">
                    <table className="w-full text-xs">
                      <thead className="bg-gray-800 text-gray-400">
                        <tr>
                          <th className="py-2 px-3 text-left">Seq</th>
                          <th className="py-2 px-3 text-left">Bin ID</th>
                          <th className="py-2 px-3 text-left">Location</th>
                          <th className="py-2 px-3 text-left">Fill %</th>
                          <th className="py-2 px-3 text-left">Waste Type</th>
                          <th className="py-2 px-3 text-left">Status</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-gray-800 text-gray-300">
                        {stops.map((s: any) => (
                          <tr key={s.id || s.bin_id} className="hover:bg-gray-800/40">
                            <td className="py-2 px-3 font-bold text-emerald-400">#{s.sequence}</td>
                            <td className="py-2 px-3 font-mono font-medium text-white">{s.bin_id}</td>
                            <td className="py-2 px-3 max-w-[150px] truncate">{s.location_name}</td>
                            <td className="py-2 px-3">{s.fill_percent?.toFixed(0)}%</td>
                            <td className="py-2 px-3">{s.waste_type}</td>
                            <td className="py-2 px-3">
                              {s.collected ? (
                                <span className="text-gray-500">Collected</span>
                              ) : (
                                <span className="text-emerald-400 font-semibold">Pending</span>
                              )}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              </div>

              {/* Dynamic Route Replanning Panel (Surge Stop Insertion) */}
              <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
                <div className="flex items-center gap-2 mb-2">
                  <ShieldCheck className="w-5 h-5 text-amber-400" />
                  <h3 className="text-sm font-bold text-white">Dynamic Route Replanning Engine (Surge Insertion)</h3>
                </div>
                <p className="text-xs text-gray-400 mb-4">
                  Simulate an urgent surge event. The replanning engine evaluates marginal detour distance, vehicle capacity compatibility, and automatically generates an approval request for the operator.
                </p>

                <div className="grid grid-cols-1 md:grid-cols-3 gap-3 items-end mb-4">
                  <div>
                    <label className="text-xs text-gray-400 block mb-1">Target Surge Bin</label>
                    <select
                      value={replanBinId}
                      onChange={(e) => setReplanBinId(e.target.value)}
                      className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-xs text-gray-200 focus:outline-none focus:border-amber-500"
                    >
                      <option value="">Select a bin...</option>
                      {availableBins.map((b) => (
                        <option key={b.bin_id} value={b.bin_id}>
                          {b.bin_id} ({b.waste_type}, {b.current_fill_percent?.toFixed(0)}% fill)
                        </option>
                      ))}
                    </select>
                  </div>

                  <div>
                    <label className="text-xs text-gray-400 block mb-1">Trigger Reason</label>
                    <input
                      type="text"
                      value={replanReason}
                      onChange={(e) => setReplanReason(e.target.value)}
                      className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-xs text-gray-200 focus:outline-none focus:border-amber-500"
                    />
                  </div>

                  <button
                    onClick={handleReplan}
                    disabled={replanning || !replanBinId}
                    className="px-4 py-2 bg-amber-600 hover:bg-amber-500 disabled:opacity-50 rounded-lg text-xs font-semibold text-white transition-colors flex items-center justify-center gap-2 h-9"
                  >
                    <Play className={`w-3.5 h-3.5 ${replanning ? 'animate-spin' : ''}`} />
                    {replanning ? 'Evaluating Detour...' : 'Trigger Replanning'}
                  </button>
                </div>

                {replanError && (
                  <div className="p-3 bg-red-950/40 border border-red-800 rounded-lg text-xs text-red-300 flex items-center gap-2">
                    <AlertCircle className="w-4 h-4 flex-shrink-0" />
                    <span>{replanError}</span>
                  </div>
                )}

                {replanResult && (
                  <div className="p-4 bg-gray-800/80 border border-emerald-700/50 rounded-lg space-y-2 text-xs">
                    <div className="flex items-center justify-between">
                      <span className="font-bold text-emerald-400">Replanning Proposal Created</span>
                      <span className="px-2 py-0.5 bg-emerald-950 text-emerald-300 rounded font-mono">
                        {replanResult.status}
                      </span>
                    </div>
                    <p className="text-gray-300">{replanResult.message || `Surge stop proposed for insertion into ${replanResult.target_route_id}`}</p>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-2 pt-2 border-t border-gray-700 text-gray-400">
                      <div>
                        <span>Marginal Detour:</span>{' '}
                        <strong className="text-white">+{replanResult.marginal_detour_km?.toFixed(2)} km</strong>
                      </div>
                      <div>
                        <span>Approval ID:</span>{' '}
                        <strong className="text-white font-mono">#{replanResult.approval_id}</strong>
                      </div>
                      <div className="col-span-2">
                        <span>Workflow:</span>{' '}
                        <strong className="text-white font-mono text-[11px]">{replanResult.workflow_id}</strong>
                      </div>
                    </div>
                    <p className="text-[11px] text-gray-400 pt-1">
                      ℹ Visit the <strong className="text-gray-200">Workflows</strong> page to review and approve this surge insertion.
                    </p>
                  </div>
                )}
              </div>
            </>
          ) : (
            <div className="bg-gray-900 border border-gray-800 rounded-xl p-12 text-center text-gray-500">
              Select a route from the directory to inspect its stops and map.
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
