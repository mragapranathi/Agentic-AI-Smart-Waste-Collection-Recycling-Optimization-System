import { Routes, Route } from 'react-router-dom'
import Layout from './components/Layout'
import Dashboard from './pages/Dashboard'
import BinsPage from './pages/BinsPage'
import MapPage from './pages/MapPage'
import PriorityPage from './pages/PriorityPage'
import ForecastingPage from './pages/ForecastingPage'
import VehiclesPage from './pages/VehiclesPage'
import RoutesPage from './pages/RoutesPage'
import CollectionsPage from './pages/CollectionsPage'
import RecyclingPage from './pages/RecyclingPage'
import AlertsPage from './pages/AlertsPage'
import WorkflowsPage from './pages/WorkflowsPage'
import ReportsPage from './pages/ReportsPage'

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Layout />}>
        <Route index element={<Dashboard />} />
        <Route path="bins" element={<BinsPage />} />
        <Route path="map" element={<MapPage />} />
        <Route path="priority" element={<PriorityPage />} />
        <Route path="forecasting" element={<ForecastingPage />} />
        <Route path="vehicles" element={<VehiclesPage />} />
        <Route path="routes" element={<RoutesPage />} />
        <Route path="collections" element={<CollectionsPage />} />
        <Route path="recycling" element={<RecyclingPage />} />
        <Route path="alerts" element={<AlertsPage />} />
        <Route path="workflows" element={<WorkflowsPage />} />
        <Route path="reports" element={<ReportsPage />} />
      </Route>
    </Routes>
  )
}
