import { useEffect, useRef } from 'react'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'

interface RouteStop {
  id?: number
  sequence: number
  bin_id: string
  location_name: string
  latitude: number
  longitude: number
  fill_percent: number
  collected: boolean
}

export default function RouteMap({ stops }: { stops: RouteStop[] }) {
  const containerRef = useRef<HTMLDivElement>(null)
  const mapRef = useRef<L.Map | null>(null)
  const layerGroupRef = useRef<L.LayerGroup | null>(null)

  useEffect(() => {
    if (!containerRef.current) return

    if (!mapRef.current) {
      const map = L.map(containerRef.current).setView([12.9716, 77.5946], 13)
      L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; OpenStreetMap contributors',
      }).addTo(map)

      const layerGroup = L.layerGroup().addTo(map)
      mapRef.current = map
      layerGroupRef.current = layerGroup
    }

    const map = mapRef.current
    const lg = layerGroupRef.current
    if (!map || !lg) return

    lg.clearLayers()

    const validStops = stops.filter((s) => s.latitude && s.longitude)
    const latLngs: L.LatLngExpression[] = []

    validStops.forEach((s) => {
      const pos: L.LatLngExpression = [s.latitude, s.longitude]
      latLngs.push(pos)

      const marker = L.circleMarker(pos, {
        radius: 9,
        color: '#ffffff',
        fillColor: s.collected ? '#9ca3af' : '#10b981',
        fillOpacity: 0.9,
        weight: 2,
      })

      marker.bindPopup(`
        <div style="font-size: 11px; line-height: 1.4;">
          <strong>Stop #${s.sequence}: ${s.bin_id}</strong><br/>
          ${s.location_name}<br/>
          Fill: <b>${(s.fill_percent ?? 0).toFixed(0)}%</b><br/>
          Status: ${s.collected ? 'Collected' : 'Pending'}
        </div>
      `)
      lg.addLayer(marker)
    })

    if (latLngs.length > 1) {
      const polyline = L.polyline(latLngs, {
        color: '#10b981',
        weight: 3,
        dashArray: '6, 6',
      })
      lg.addLayer(polyline)
    }

    if (validStops.length > 0) {
      const bounds = L.latLngBounds(latLngs)
      map.fitBounds(bounds, { padding: [30, 30] })
    }
  }, [stops])

  return (
    <div ref={containerRef} style={{ height: '100%', width: '100%', minHeight: '260px' }} />
  )
}
