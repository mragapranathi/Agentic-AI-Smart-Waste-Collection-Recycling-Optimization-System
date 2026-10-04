import { api } from './client'

// ── Bins ──────────────────────────────────────────────────────────────────────
export const getBins = (params?: Record<string, any>) =>
  api.get('/bins', { params }).then((r) => r.data)

export const getBin = (binId: string) =>
  api.get(`/bins/${binId}`).then((r) => r.data)

export const createBin = (payload: Record<string, any>) =>
  api.post('/bins', payload).then((r) => r.data)

export const updateBin = (binId: string, payload: Record<string, any>) =>
  api.put(`/bins/${binId}`, payload).then((r) => r.data)

export const deleteBin = (binId: string) =>
  api.delete(`/bins/${binId}`).then((r) => r.data)

// ── Sensor Readings ───────────────────────────────────────────────────────────
export const submitReading = (payload: Record<string, any>) =>
  api.post('/sensors/readings', payload).then((r) => r.data)

export const getAlerts = (params?: Record<string, any>) =>
  api.get('/sensors/alerts', { params }).then((r) => r.data)

export const resolveAlert = (alertId: number) =>
  api.put(`/sensors/alerts/${alertId}/resolve`).then((r) => r.data)

// ── Forecasts ─────────────────────────────────────────────────────────────────
export const runForecast = (binId?: string, horizonHours = 24) =>
  api.post('/forecasts/run', { bin_ids: binId ? [binId] : undefined, horizon_hours: horizonHours })
     .then((r) => (binId && Array.isArray(r.data) ? r.data[0] : r.data))

export const getForecasts = (params?: Record<string, any>) =>
  api.get('/forecasts', { params }).then((r) => r.data)

export const getModelMetadata = () =>
  api.get('/forecasts/model-metadata').then((r) => r.data)

// ── Priorities ────────────────────────────────────────────────────────────────
export const getPriorities = () =>
  api.get('/priorities').then((r) => r.data)

export const calculatePriorities = () =>
  api.post('/priorities/calculate').then((r) => r.data)

// ── Vehicles ──────────────────────────────────────────────────────────────────
export const getVehicles = (params?: Record<string, any>) =>
  api.get('/vehicles', { params }).then((r) => r.data)

export const createVehicle = (payload: Record<string, any>) =>
  api.post('/vehicles', payload).then((r) => r.data)

export const updateVehicle = (vehicleId: string, payload: Record<string, any>) =>
  api.put(`/vehicles/${vehicleId}`, payload).then((r) => r.data)

export const deleteVehicle = (vehicleId: string) =>
  api.delete(`/vehicles/${vehicleId}`).then((r) => r.data)

// ── Routes ────────────────────────────────────────────────────────────────────
export const optimizeRoutes = (payload?: Record<string, any>) =>
  api.post('/routes/optimize', payload).then((r) => r.data)


export const getRoutes = (params?: Record<string, any>) =>
  api.get('/routes', { params }).then((r) => r.data)

export const getRoute = (routeId: string) =>
  api.get(`/routes/${routeId}`).then((r) => r.data)

export const replanRoute = (routeId: string, payload: Record<string, any>) =>
  api.post(`/routes/${routeId}/replan`, payload).then((r) => r.data)

// ── Collections ───────────────────────────────────────────────────────────────
export const getCollections = (params?: Record<string, any>) =>
  api.get('/collections', { params }).then((r) => r.data)

export const updateCollection = (collectionId: string, payload: Record<string, any>) =>
  api.put(`/collections/${collectionId}`, payload).then((r) => r.data)

// ── Recycling ─────────────────────────────────────────────────────────────────
export const getRecyclingAnalytics = (params?: Record<string, any>) =>
  api.get('/recycling/analytics', { params }).then((r) => r.data)

export const getRecyclingRecords = (params?: Record<string, any>) =>
  api.get('/recycling/records', { params }).then((r) => r.data)

// ── Dashboard ─────────────────────────────────────────────────────────────────
export const getDashboardKPIs = () =>
  api.get('/dashboard/kpis').then((r) => r.data)

// ── Workflows ─────────────────────────────────────────────────────────────────
export const runWorkflow = (payload?: Record<string, any>) =>
  api.post('/workflows/run', payload ?? {}).then((r) => r.data)

export const getWorkflows = (params?: Record<string, any>) =>
  api.get('/workflows', { params }).then((r) => r.data)

export const getWorkflow = (workflowId: string) =>
  api.get(`/workflows/${workflowId}`).then((r) => r.data)

// ── Approvals ─────────────────────────────────────────────────────────────────
export const getApprovals = (params?: Record<string, any>) =>
  api.get('/approvals', { params }).then((r) => r.data)

export const approveWorkflow = (workflowId: string, operator: string, comment?: string) =>
  api.post(`/approvals/${workflowId}/approve`, { operator, comment }).then((r) => r.data)

export const rejectWorkflow = (workflowId: string, operator: string, comment?: string) =>
  api.post(`/approvals/${workflowId}/reject`, { operator, comment }).then((r) => r.data)

// ── Agent Runs ────────────────────────────────────────────────────────────────
export const getAgentRuns = (workflowId: string) =>
  api.get(`/agent-runs/${workflowId}`).then((r) => r.data)

// ── Reports ───────────────────────────────────────────────────────────────────
export const generateReport = (payload: Record<string, any>) =>
  api.post('/reports/generate', payload).then((r) => r.data)

export const listReports = () =>
  api.get('/reports').then((r) => r.data)

// ── Health ────────────────────────────────────────────────────────────────────
export const getHealth = () =>
  api.get('/health').then((r) => r.data)
