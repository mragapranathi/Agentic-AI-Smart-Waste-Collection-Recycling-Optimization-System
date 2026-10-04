import { useEffect, useRef, useState, useCallback } from 'react'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import { getBins, getVehicles, getRoutes } from '../api/endpoints'
import { Map as MapIcon, RefreshCw, Filter, Truck, Trash2, Navigation } from 'lucide-react'

const FILL_COLOR = (fill: number) => {
  if (fill >= 90) return '#ef4444'
  if (fill >= 75) return '#f97316'
  if (fill >= 50) return '#eab308'
  return '#22c55e'
}

export default function MapPage() {
  const mapContainerRef = useRef<HTMLDivElement>(null)
  const mapRef = useRef<L.Map | null>(null)
  const binsLayerRef = useRef<L.LayerGroup | null>(null)
  const vehiclesLayerRef = useRef<L.LayerGroup | null>(null)
  const routesLayerRef = useRef<L.LayerGroup | null>(null)

  const [bins, setBins] = useState<any[]>([])
  const [vehicles, setVehicles] = useState<any[]>([])
  const [routes, setRoutes] = useState<any[]>([])
  const [loading, setLoading] = useState(true)

  // Toggles & filters
  const [showBins, setShowBins] = useState(true)
  const [showVehicles, setShowVehicles] = useState(true)
  const [showRoutes, setShowRoutes] = useState(true)
  const [wasteFilter, setWasteFilter] = useState('ALL')

  const loadData = useCallback(async () => {
    setLoading(true)
    try {
      const [b, v, r] = await Promise.all([
        getBins({ limit: 200 }),
        getVehicles({ limit: 50 }),
        getRoutes({ limit: 20 })
      ])
      setBins(b)
      setVehicles(v)
      setRoutes(r)
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { loadData() }, [loadData])

  // Initialize Map
  useEffect(() => {
    if (!mapContainerRef.current) return

    if (!mapRef.current) {
      const map = L.map(mapContainerRef.current).setView([12.9716, 77.5946], 13)
      L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; OpenStreetMap contributors',
      }).addTo(map)

      binsLayerRef.current = L.layerGroup().addTo(map)
      vehiclesLayerRef.current = L.layerGroup().addTo(map)
      routesLayerRef.current = L.layerGroup().addTo(map)
      mapRef.current = map
    }
  }, [])

  // Render Markers and Polylines
  useEffect(() => {
    const map = mapRef.current
    const bl = binsLayerRef.current
    const vl = vehiclesLayerRef.current
    const rl = routesLayerRef.current
    if (!map || !bl || !vl || !rl) return

    bl.clearLayers()
    vl.clearLayers()
    rl.clearLayers()

    // 1. Render Bins
    if (showBins) {
      const filteredBins = wasteFilter === 'ALL'
        ? bins
        : bins.filter((b) => b.waste_type === wasteFilter)

      filteredBins.forEach((b) => {
        if (!b.latitude || !b.longitude) return
        const marker = L.circleMarker([b.latitude, b.longitude], {
          radius: 8,
          color: '#ffffff',
          fillColor: FILL_COLOR(b.current_fill_percent ?? 0),
          fillOpacity: 0.9,
          weight: 1.5,
        })

        marker.bindPopup(`
          <div style="font-size: 12px; line-height: 1.5; min-width: 160px;">
            <div style="font-weight: bold; font-size: 13px; color: #10b981; margin-bottom: 2px;">${b.bin_id}</div>
            <div><strong>Location:</strong> ${b.location_name}</div>
            <div><strong>Fill Level:</strong> <span style="font-weight: bold; color: ${FILL_COLOR(b.current_fill_percent ?? 0)}">${(b.current_fill_percent ?? 0).toFixed(0)}%</span></div>
            <div><strong>Weight:</strong> ${(b.current_weight_kg ?? 0).toFixed(1)} kg</div>
            <div><strong>Stream:</strong> ${b.waste_type}</div>
            <div><strong>Battery:</strong> ${(b.battery_level ?? 100).toFixed(0)}%</div>
            <div><strong>Sensor:</strong> ${b.sensor_status}</div>
          </div>
        `)
        bl.addLayer(marker)
      })
    }

    // 2. Render Vehicles
    if (showVehicles) {
      vehicles.forEach((v) => {
        if (!v.latitude || !v.longitude) return
        const vMarker = L.circleMarker([v.latitude, v.longitude], {
          radius: 11,
          color: '#3b82f6',
          fillColor: '#1d4ed8',
          fillOpacity: 0.95,
          weight: 2,
        })

        const util = Math.min(100, ((v.current_load_liters ?? 0) / (v.capacity_liters ?? 1)) * 100)
        vMarker.bindPopup(`
          <div style="font-size: 12px; line-height: 1.5; min-width: 170px;">
            <div style="font-weight: bold; font-size: 13px; color: #3b82f6; margin-bottom: 2px;">${v.vehicle_id}</div>
            <div><strong>Status:</strong> ${v.status}</div>
            <div><strong>Capacity:</strong> ${v.capacity_liters?.toFixed(0)} L</div>
            <div><strong>Current Load:</strong> ${v.current_load_liters?.toFixed(0)} L (${util.toFixed(0)}%)</div>
            <div><strong>Streams:</strong> ${(v.supported_waste_types ?? []).join(', ')}</div>
          </div>
        `)
        vl.addLayer(vMarker)
      })
    }

    // 3. Render Routes
    if (showRoutes) {
      routes.forEach((r, idx) => {
        const stops = r.stops ?? []
        const coords: L.LatLngExpression[] = stops
          .filter((s: any) => s.latitude && s.longitude)
          .map((s: any) => [s.latitude, s.longitude] as [number, number])

        if (coords.length > 1) {
          const colorList = ['#10b981', '#f59e0b', '#8b5cf6', '#06b6d4', '#ec4899']
          const polyline = L.polyline(coords, {
            color: colorList[idx % colorList.length],
            weight: 3.5,
            dashArray: '5, 5',
          })
          polyline.bindPopup(`
            <div style="font-size: 12px;">
              <strong>Route: ${r.route_id}</strong><br/>
              Vehicle: ${r.vehicle_id}<br/>
              Stops: ${stops.length} bins<br/>
              Distance: ${r.total_distance_km?.toFixed(1)} km
            </div>
          `)
          rl.addLayer(polyline)
        }
      })
    }
  }, [bins, vehicles, routes, showBins, showVehicles, showRoutes, wasteFilter])

  return (
    <div className="h-full flex flex-col">
      {/* Top Controls Bar */}
      <div className="p-4 bg-gray-900 border-b border-gray-800 flex items-center justify-between flex-wrap gap-4 z-10">
        <div>
          <h1 className="text-xl font-bold text-white flex items-center gap-2">
            <MapIcon className="w-5 h-5 text-emerald-400" /> Municipal GIS Live Operations Map
          </h1>
          <p className="text-gray-400 text-xs mt-0.5">
            Real-time geospatial tracking for smart bins, vehicle telemetry, and dispatched routes
          </p>
        </div>

        {/* Filter and Layer Toggles */}
        <div className="flex items-center gap-3 flex-wrap">
          {/* Waste stream filter */}
          <div className="flex items-center gap-1.5 bg-gray-800 px-3 py-1.5 rounded-lg border border-gray-700 text-xs">
            <Filter className="w-3.5 h-3.5 text-gray-400" />
            <select
              value={wasteFilter}
              onChange={(e) => setWasteFilter(e.target.value)}
              className="bg-transparent text-gray-200 focus:outline-none"
            >
              <option value="ALL">All Streams</option>
              <option value="General">General</option>
              <option value="Recyclable">Recyclable</option>
              <option value="Organic">Organic</option>
            </select>
          </div>

          {/* Layer toggles */}
          <div className="flex items-center gap-1 bg-gray-800 p-1 rounded-lg border border-gray-700 text-xs">
            <button
              onClick={() => setShowBins(!showBins)}
              className={`px-2.5 py-1 rounded flex items-center gap-1.5 transition-colors ${
                showBins ? 'bg-emerald-600 text-white font-medium' : 'text-gray-400 hover:text-gray-200'
              }`}
            >
              <Trash2 className="w-3 h-3" /> Bins ({bins.length})
            </button>
            <button
              onClick={() => setShowVehicles(!showVehicles)}
              className={`px-2.5 py-1 rounded flex items-center gap-1.5 transition-colors ${
                showVehicles ? 'bg-blue-600 text-white font-medium' : 'text-gray-400 hover:text-gray-200'
              }`}
            >
              <Truck className="w-3 h-3" /> Vehicles ({vehicles.length})
            </button>
            <button
              onClick={() => setShowRoutes(!showRoutes)}
              className={`px-2.5 py-1 rounded flex items-center gap-1.5 transition-colors ${
                showRoutes ? 'bg-amber-600 text-white font-medium' : 'text-gray-400 hover:text-gray-200'
              }`}
            >
              <Navigation className="w-3 h-3" /> Routes ({routes.length})
            </button>
          </div>

          <button
            onClick={loadData}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-gray-800 hover:bg-gray-700 border border-gray-700 rounded-lg text-xs text-gray-300 transition-colors"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} /> Refresh
          </button>
        </div>
      </div>

      {/* Map Container */}
      <div className="flex-1 relative">
        <div ref={mapContainerRef} className="absolute inset-0" />

        {/* Legend Overlay */}
        <div className="absolute bottom-6 right-6 bg-gray-900/90 backdrop-blur border border-gray-800 p-3 rounded-xl shadow-xl text-xs space-y-1.5 z-[1000]">
          <span className="font-bold text-gray-200 block mb-1">Fill Legend</span>
          <div className="flex items-center gap-2">
            <span className="w-3 h-3 rounded-full bg-red-500" />
            <span className="text-gray-300">&ge; 90% (Critical Overflow)</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-3 h-3 rounded-full bg-orange-500" />
            <span className="text-gray-300">75% - 89% (High Priority)</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-3 h-3 rounded-full bg-yellow-500" />
            <span className="text-gray-300">50% - 74% (Moderate)</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-3 h-3 rounded-full bg-emerald-500" />
            <span className="text-gray-300">&lt; 50% (Normal)</span>
          </div>
          <div className="flex items-center gap-2 pt-1 border-t border-gray-800">
            <span className="w-3 h-3 rounded-full bg-blue-600 border border-blue-400" />
            <span className="text-gray-300">Fleet Vehicle</span>
          </div>
        </div>
      </div>
    </div>
  )
}
