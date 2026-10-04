import { useEffect, useState, useCallback } from 'react'
import { getWorkflows, runWorkflow, approveWorkflow, rejectWorkflow } from '../api/endpoints'
import {
  Workflow, Play, CheckCircle2, XCircle, ShieldCheck, RefreshCw, Bot
} from 'lucide-react'

const AGENT_ORDER = [
  { key: 'Smart Bin Monitoring Agent',                  name: 'Bin Monitoring',    desc: 'Validates sensor data & health' },
  { key: 'Waste Generation Forecasting Agent',          name: 'ML Forecasting',    desc: 'Predicts fill growth & thresholds' },
  { key: 'Collection Priority Agent',                   name: 'Priority Engine',   desc: 'Calculates urgency & overflow risk' },
  { key: 'Vehicle & Capacity Management Agent',         name: 'Vehicle Capacity',  desc: 'Filters available fleet & limits' },
  { key: 'Route Optimization Agent',                    name: 'OR-Tools CVRP',     desc: 'Computes optimal multi-stop routes' },
  { key: 'Recycling & Segregation Agent',               name: 'Recycling Audit',   desc: 'Audits contamination & segregation' },
  { key: 'Waste Operations & Action Planning Agent',    name: 'Action Planning',   desc: 'Packages dispatchable plan' },
  { key: 'Operations Reviewer / Critic Agent',          name: 'Reviewer & Critic', desc: 'Validates safety & approves/replans' },
]

export default function WorkflowsPage() {
  const [workflows, setWorkflows] = useState<any[]>([])
  const [selectedWorkflow, setSelectedWorkflow] = useState<any | null>(null)
  const [loading, setLoading] = useState(true)
  const [running, setRunning] = useState(false)
  const [operatorName, setOperatorName] = useState('Chief Municipal Dispatcher')
  const [approvalComment, setApprovalComment] = useState('Reviewed capacity and routing constraints; approved for execution.')
  const [actionLoading, setActionLoading] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const data = await getWorkflows({ limit: 20 })
      setWorkflows(data)
      if (data.length > 0 && !selectedWorkflow) {
        setSelectedWorkflow(data[0])
      } else if (selectedWorkflow) {
        const updated = data.find((w: any) => w.workflow_id === selectedWorkflow.workflow_id)
        if (updated) setSelectedWorkflow(updated)
      }
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }, [selectedWorkflow])

  useEffect(() => { load() }, [])

  const handleRunWorkflow = async () => {
    setRunning(true)
    try {
      const res = await runWorkflow({ planning_period_hours: 24 })
      await load()
      setSelectedWorkflow(res)
    } catch (e: any) {
      alert(`Workflow execution failed: ${e.message}`)
    } finally {
      setRunning(false)
    }
  }

  const handleApprove = async () => {
    if (!selectedWorkflow) return
    setActionLoading(true)
    try {
      await approveWorkflow(selectedWorkflow.workflow_id, operatorName, approvalComment)
      await load()
    } catch (e: any) {
      alert(`Approval failed: ${e.message}`)
    } finally {
      setActionLoading(false)
    }
  }

  const handleReject = async () => {
    if (!selectedWorkflow) return
    setActionLoading(true)
    try {
      await rejectWorkflow(selectedWorkflow.workflow_id, operatorName, approvalComment)
      await load()
    } catch (e: any) {
      alert(`Rejection failed: ${e.message}`)
    } finally {
      setActionLoading(false)
    }
  }

  const agentRunsMap = (selectedWorkflow?.agent_runs ?? []).reduce((acc: any, r: any) => {
    acc[r.agent_name] = r
    // Comprehensive key fallbacks so both UI schemas map seamlessly
    if (r.agent_name.includes('Action Planning')) {
      acc['Waste Operations & Action Planning Agent'] = r
      acc['Action Planning Agent'] = r
    }
    if (r.agent_name.includes('Reviewer') || r.agent_name.includes('Critic')) {
      acc['Operations Reviewer / Critic Agent'] = r
      acc['Reviewer & Critic Agent'] = r
    }
    if (r.agent_name.includes('Monitoring')) acc['Smart Bin Monitoring Agent'] = r
    if (r.agent_name.includes('Forecasting')) acc['Waste Generation Forecasting Agent'] = r
    if (r.agent_name.includes('Priority')) acc['Collection Priority Agent'] = r
    if (r.agent_name.includes('Vehicle')) acc['Vehicle & Capacity Management Agent'] = r
    if (r.agent_name.includes('Route')) acc['Route Optimization Agent'] = r
    if (r.agent_name.includes('Recycling')) acc['Recycling & Segregation Agent'] = r
    return acc
  }, {})

  const approval = selectedWorkflow?.approval_request
  const plan = approval?.proposed_plan

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-2">
            <Workflow className="w-6 h-6 text-emerald-400" /> Multi-Agent Orchestration & Governance
          </h1>
          <p className="text-gray-400 text-sm mt-0.5">
            8 Specialized Agents · LangGraph Stateful Workflow · Human-in-the-Loop Governance
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
            onClick={handleRunWorkflow}
            disabled={running}
            className="flex items-center gap-2 px-4 py-2 bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 rounded-lg text-sm font-semibold text-white transition-colors"
          >
            <Play className={`w-4 h-4 ${running ? 'animate-spin' : ''}`} />
            {running ? 'Orchestrating 8 Agents...' : 'Trigger Planning Workflow'}
          </button>
        </div>
      </div>

      {/* 8-Agent Visual Architecture Pipeline */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
        <h2 className="text-sm font-bold text-white mb-3 flex items-center gap-2">
          <Bot className="w-4 h-4 text-emerald-400" /> 8-Agent Decision Pipeline Architecture
        </h2>
        <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-8 gap-2">
          {AGENT_ORDER.map((agent, idx) => {
            const run = agentRunsMap[agent.key]
            const isSuccess = run?.status === 'SUCCESS'
            const isFailed = run?.status === 'FAILED'

            return (
              <div
                key={agent.key}
                className={`p-3 rounded-lg border text-center relative ${
                  isSuccess
                    ? 'border-emerald-700 bg-emerald-950/30'
                    : isFailed
                    ? 'border-red-700 bg-red-950/30'
                    : 'border-gray-800 bg-gray-800/30'
                }`}
              >
                <div className="text-[10px] text-gray-500 font-mono mb-1">AGENT 0{idx + 1}</div>
                <div className="font-semibold text-xs text-white truncate" title={agent.name}>
                  {agent.name}
                </div>
                <div className="text-[10px] text-gray-400 mt-1 line-clamp-2">{agent.desc}</div>
                <div className="mt-2">
                  {isSuccess ? (
                    <span className="inline-flex items-center gap-1 text-[10px] font-bold text-emerald-400">
                      <CheckCircle2 className="w-3 h-3" /> Done
                    </span>
                  ) : isFailed ? (
                    <span className="inline-flex items-center gap-1 text-[10px] font-bold text-red-400">
                      <XCircle className="w-3 h-3" /> Error
                    </span>
                  ) : (
                    <span className="text-[10px] text-gray-600">Pending</span>
                  )}
                </div>
              </div>
            )
          })}
        </div>
      </div>

      {/* Main Grid: Workflow Runs List & Selected Run Details */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left: Workflows Runs Directory */}
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-5 space-y-4">
          <div className="flex items-center justify-between">
            <span className="text-sm font-semibold text-white">Execution History ({workflows.length})</span>
            <span className="text-xs text-gray-500">Most recent first</span>
          </div>

          {workflows.length === 0 ? (
            <div className="py-12 text-center text-gray-500 text-sm">
              <Workflow className="w-8 h-8 mx-auto mb-2 text-gray-600" />
              No workflows executed yet.<br />
              Click "Trigger Planning Workflow" to begin.
            </div>
          ) : (
            <div className="space-y-3 max-h-[580px] overflow-y-auto pr-1">
              {workflows.map((w) => {
                const isSelected = selectedWorkflow?.workflow_id === w.workflow_id
                return (
                  <div
                    key={w.workflow_id}
                    onClick={() => setSelectedWorkflow(w)}
                    className={`p-4 rounded-xl border cursor-pointer transition-all ${
                      isSelected
                        ? 'border-emerald-500 bg-emerald-950/20'
                        : 'border-gray-800 bg-gray-800/40 hover:bg-gray-800 hover:border-gray-700'
                    }`}
                  >
                    <div className="flex items-center justify-between mb-2">
                      <span className="font-mono text-xs font-bold text-white">{w.workflow_id}</span>
                      <span className={`px-2 py-0.5 rounded text-[11px] font-semibold ${
                        w.status === 'COMPLETED' ? 'bg-emerald-900 text-emerald-300' :
                        w.status === 'WAITING_APPROVAL' ? 'bg-amber-900 text-amber-300' :
                        w.status === 'REJECTED' ? 'bg-red-900 text-red-300' :
                        'bg-blue-900 text-blue-300'
                      }`}>
                        {w.status}
                      </span>
                    </div>

                    <div className="text-xs text-gray-400 space-y-1">
                      <div className="flex justify-between">
                        <span>Current State:</span>
                        <span className="text-gray-200 font-mono">{w.current_state}</span>
                      </div>
                      <div className="flex justify-between">
                        <span>Agents Executed:</span>
                        <span className="text-gray-200">
                          {Math.min(8, new Set((w.agent_runs || []).map((r: any) => r.agent_name)).size)} / 8
                          {(w.agent_runs?.length ?? 0) > 8 ? ' (Replanned)' : ''}
                        </span>
                      </div>
                      <div className="flex justify-between">
                        <span>Timestamp:</span>
                        <span className="text-gray-400 font-mono text-[11px]">
                          {w.started_at ? new Date(w.started_at).toLocaleTimeString() : '—'}
                        </span>
                      </div>
                    </div>
                  </div>
                )
              })}
            </div>
          )}
        </div>

        {/* Right 2 cols: Selected Workflow Inspector & Approval Gate */}
        <div className="lg:col-span-2 space-y-6">
          {selectedWorkflow ? (
            <>
              {/* Human-in-the-Loop Approval Decision Card */}
              {approval ? (
                <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
                  <div className="flex items-center justify-between mb-4 border-b border-gray-800 pb-3">
                    <div className="flex items-center gap-2">
                      <ShieldCheck className="w-5 h-5 text-amber-400" />
                      <h3 className="text-base font-bold text-white">Human Approval Gate</h3>
                    </div>
                    <span className={`px-3 py-1 rounded-full text-xs font-bold ${
                      approval.status === 'APPROVED' ? 'bg-emerald-900 text-emerald-300 border border-emerald-700' :
                      approval.status === 'REJECTED' ? 'bg-red-900 text-red-300 border border-red-700' :
                      'bg-amber-900 text-amber-300 border border-amber-700 animate-pulse'
                    }`}>
                      {approval.status}
                    </span>
                  </div>

                  {plan && (
                    <div className="p-4 bg-gray-800/60 rounded-xl mb-4 text-xs space-y-3">
                      <p className="font-semibold text-gray-200 text-sm">Proposed Operational Dispatch Plan</p>
                      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-gray-300">
                        <div className="bg-gray-800 p-2.5 rounded-lg">
                          <span className="text-gray-500 block">Proposed Routes</span>
                          <span className="text-lg font-bold text-white">{plan.routes?.length ?? 0}</span>
                        </div>
                        <div className="bg-gray-800 p-2.5 rounded-lg">
                          <span className="text-gray-500 block">Total Distance</span>
                          <span className="text-lg font-bold text-white">{(plan.total_distance_km ?? 0).toFixed(1)} km</span>
                        </div>
                        <div className="bg-gray-800 p-2.5 rounded-lg">
                          <span className="text-gray-500 block">Est. Duration</span>
                          <span className="text-lg font-bold text-white">{(plan.estimated_duration_minutes ?? 0).toFixed(0)} min</span>
                        </div>
                        <div className="bg-gray-800 p-2.5 rounded-lg">
                          <span className="text-gray-500 block">Unassigned Bins</span>
                          <span className="text-lg font-bold text-white">{plan.unassigned_bins?.length ?? 0}</span>
                        </div>
                      </div>

                      {plan.critic_evaluation && (
                        <div className="p-3 bg-gray-900 rounded-lg border border-gray-700">
                          <span className="text-gray-400 font-semibold block mb-1">Critic Agent Audit Evaluation:</span>
                          <p className="text-gray-300 leading-relaxed">{plan.critic_evaluation}</p>
                        </div>
                      )}
                    </div>
                  )}

                  {approval.status === 'PENDING' ? (
                    <div className="space-y-3 pt-2">
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                        <div>
                          <label className="text-xs text-gray-400 block mb-1">Authorized Operator Name</label>
                          <input
                            type="text"
                            value={operatorName}
                            onChange={(e) => setOperatorName(e.target.value)}
                            className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-xs text-gray-200 focus:outline-none focus:border-emerald-500"
                          />
                        </div>
                        <div>
                          <label className="text-xs text-gray-400 block mb-1">Decision Comments / Notes</label>
                          <input
                            type="text"
                            value={approvalComment}
                            onChange={(e) => setApprovalComment(e.target.value)}
                            className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-xs text-gray-200 focus:outline-none focus:border-emerald-500"
                          />
                        </div>
                      </div>

                      <div className="flex gap-3 pt-2">
                        <button
                          onClick={handleApprove}
                          disabled={actionLoading}
                          className="flex-1 py-2.5 bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 rounded-lg text-xs font-bold text-white transition-colors flex items-center justify-center gap-2"
                        >
                          <CheckCircle2 className="w-4 h-4" />
                          Approve Plan & Activate Routes
                        </button>
                        <button
                          onClick={handleReject}
                          disabled={actionLoading}
                          className="px-6 py-2.5 bg-red-800 hover:bg-red-700 disabled:opacity-50 rounded-lg text-xs font-bold text-white transition-colors flex items-center justify-center gap-2"
                        >
                          <XCircle className="w-4 h-4" />
                          Reject Plan
                        </button>
                      </div>
                    </div>
                  ) : (
                    <div className="p-3 bg-gray-800/80 rounded-lg text-xs text-gray-300 space-y-1">
                      <div className="flex justify-between">
                        <span>Decided By:</span>
                        <strong className="text-white">{approval.operator || 'Unknown Operator'}</strong>
                      </div>
                      <div className="flex justify-between">
                        <span>Operator Notes:</span>
                        <span className="text-gray-400">{approval.comment || 'No comment provided.'}</span>
                      </div>
                      <div className="flex justify-between">
                        <span>Timestamp:</span>
                        <span className="font-mono text-gray-400">
                          {approval.decided_at ? new Date(approval.decided_at).toLocaleString() : '—'}
                        </span>
                      </div>
                    </div>
                  )}
                </div>
              ) : null}

              {/* Agent Runs Execution Telemetry Trace */}
              <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
                <h3 className="text-sm font-bold text-white mb-4 flex items-center gap-2">
                  <Bot className="w-4 h-4 text-emerald-400" /> Agent Execution Telemetry & Reasoning Trace
                </h3>

                <div className="space-y-3">
                  {AGENT_ORDER.map((agentConfig) => {
                    const run = agentRunsMap[agentConfig.key]
                    if (!run) return null
                    return (
                      <div
                        key={agentConfig.key}
                        className="p-4 bg-gray-800/50 border border-gray-800 rounded-xl space-y-2 text-xs"
                      >
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-2">
                            <span className={`w-2.5 h-2.5 rounded-full ${
                              run.status === 'SUCCESS' ? 'bg-emerald-500' : 'bg-red-500'
                            }`} />
                            <span className="font-bold text-white">{run.agent_name}</span>
                          </div>
                          <span className="font-mono text-[11px] text-gray-400">
                            {run.completed_at ? new Date(run.completed_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }) : 'Done'}
                          </span>
                        </div>

                        <p className="text-gray-300 leading-relaxed pl-4 border-l-2 border-emerald-500/30">
                          {run.reasoning_summary}
                        </p>
                      </div>
                    )
                  })}
                </div>
              </div>
            </>
          ) : (
            <div className="bg-gray-900 border border-gray-800 rounded-xl p-12 text-center text-gray-500">
              Select an execution run to inspect the agent telemetry trace.
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
