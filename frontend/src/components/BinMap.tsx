import { useEffect, useRef, useState } from 'react'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import { getBins } from '../api/endpoints'

const FILL_COLOR = (fill: number) => {
  if (fill >= 90) return '#ef4444'
  if (fill >= 75) return '#f97316'
  if (fill >= 50) return '#eab308'
  return '#22c55e'
}

export default function BinMap({ height = '100%' }: { height?: string }) {
  const mapContainerRef = useRef<HTMLDivElement>(null)
  const mapInstanceRef = useRef<L.Map | null>(null)
  const [bins, setBins] = useState<any[]>([])

  useEffect(() => {
    getBins({ limit: 200 }).then(setBins).catch(console.error)
  }, [])

  useEffect(() => {
    if (!mapContainerRef.current) return

    if (!mapInstanceRef.current) {
      const initialCenter: [number, number] = bins.length > 0
        ? [bins[0].latitude, bins[0].longitude]
        : [12.9716, 77.5946]

      const map = L.map(mapContainerRef.current).setView(initialCenter, 13)
      L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; OpenStreetMap contributors'
      }).addTo(map)

      mapInstanceRef.current = map
    }

    const map = mapInstanceRef.current

    // Clear previous markers
    map.eachLayer((layer) => {
      if (layer instanceof L.CircleMarker) {
        map.removeLayer(layer)
      }
    })

    if (bins.length > 0) {
      bins.forEach((b) => {
        if (!b.latitude || !b.longitude) return
        const marker = L.circleMarker([b.latitude, b.longitude], {
          radius: 8,
          color: '#ffffff',
          fillColor: FILL_COLOR(b.current_fill_percent ?? 0),
          fillOpacity: 0.9,
          weight: 1.5,
        })

        marker.bindPopup(`
          <div style="font-size: 11px; line-height: 1.4;">
            <strong>${b.bin_id}</strong><br/>
            ${b.location_name}<br/>
            Fill: <b>${(b.current_fill_percent ?? 0).toFixed(0)}%</b><br/>
            Type: ${b.waste_type}<br/>
            Sensor: ${b.sensor_status}
          </div>
        `)
        marker.addTo(map)
      })

      map.setView([bins[0].latitude, bins[0].longitude], 13)
    }

    return () => {
      // Keep map instance mounted
    }
  }, [bins])

  return (
    <div ref={mapContainerRef} style={{ height, width: '100%' }} />
  )
}
