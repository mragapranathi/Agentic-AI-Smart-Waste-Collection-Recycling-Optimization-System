import { useEffect, useState, useCallback } from 'react'
import { generateReport, listReports } from '../api/endpoints'
import { FileText, Download, Play, RefreshCw, CheckCircle2, ShieldCheck } from 'lucide-react'

export default function ReportsPage() {
  const [reports, setReports] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [generating, setGenerating] = useState(false)
  const [periodDays, setPeriodDays] = useState(7)
  const [reportTitle, setReportTitle] = useState('Municipal Waste Operations & Recycling Optimization Audit')
  const [latestReport, setLatestReport] = useState<any | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const data = await listReports()
      setReports(data)
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load() }, [load])

  const handleGenerate = async () => {
    setGenerating(true)
    try {
      const res = await generateReport({
        period_days: periodDays,
        title: reportTitle,
      })
      setLatestReport(res)
      await load()
    } catch (e: any) {
      alert(`Report generation failed: ${e.message}`)
    } finally {
      setGenerating(false)
    }
  }

  const handleDownload = (downloadUrl: string) => {
    // Open download in a new tab or trigger directly
    const fullUrl = downloadUrl.startsWith('http') ? downloadUrl : `http://localhost:8000${downloadUrl}`
    window.open(fullUrl, '_blank')
  }

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-2">
            <FileText className="w-6 h-6 text-emerald-400" /> Operational & Audit Reports
          </h1>
          <p className="text-gray-400 text-sm mt-0.5">
            Automated PDF generation with ReportLab · Audit trails · Municipal compliance metrics
          </p>
        </div>
        <button
          onClick={load}
          className="flex items-center gap-2 px-3 py-2 bg-gray-800 hover:bg-gray-700 rounded-lg text-sm text-gray-300 transition-colors"
        >
          <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} /> Refresh
        </button>
      </div>

      {/* Generator Card */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-5 space-y-4">
        <div className="flex items-center gap-2 border-b border-gray-800 pb-3">
          <ShieldCheck className="w-5 h-5 text-emerald-400" />
          <h2 className="text-sm font-bold text-white">Generate Official Municipal Audit Report (PDF)</h2>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 items-end">
          <div className="md:col-span-2">
            <label className="text-xs text-gray-400 block mb-1">Report Document Title</label>
            <input
              type="text"
              value={reportTitle}
              onChange={(e) => setReportTitle(e.target.value)}
              className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-xs text-gray-200 focus:outline-none focus:border-emerald-500"
            />
          </div>

          <div>
            <label className="text-xs text-gray-400 block mb-1">Audit Time Horizon</label>
            <select
              value={periodDays}
              onChange={(e) => setPeriodDays(Number(e.target.value))}
              className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-xs text-gray-200 focus:outline-none focus:border-emerald-500"
            >
              <option value={7}>Last 7 Days Audit</option>
              <option value={14}>Last 14 Days Audit</option>
              <option value={30}>Last 30 Days Audit</option>
              <option value={90}>Quarterly Audit (90 Days)</option>
            </select>
          </div>
        </div>

        <button
          onClick={handleGenerate}
          disabled={generating}
          className="px-5 py-2.5 bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 rounded-lg text-xs font-bold text-white transition-colors flex items-center justify-center gap-2"
        >
          <Play className={`w-3.5 h-3.5 ${generating ? 'animate-spin' : ''}`} />
          {generating ? 'Compiling PDF via ReportLab...' : 'Generate Official PDF Report'}
        </button>

        {latestReport && (
          <div className="p-4 bg-emerald-950/30 border border-emerald-700/60 rounded-lg flex items-center justify-between flex-wrap gap-3">
            <div className="flex items-center gap-2">
              <CheckCircle2 className="w-5 h-5 text-emerald-400" />
              <div>
                <p className="text-xs font-bold text-white">Report Successfully Compiled!</p>
                <p className="text-[11px] text-gray-400 font-mono">{latestReport.report_id}</p>
              </div>
            </div>
            <button
              onClick={() => handleDownload(latestReport.download_url)}
              className="flex items-center gap-1.5 px-3 py-1.5 bg-emerald-600 hover:bg-emerald-500 rounded text-xs font-semibold text-white transition-colors"
            >
              <Download className="w-3.5 h-3.5" /> Download PDF
            </button>
          </div>
        )}
      </div>

      {/* Available Downloadable Reports Archive */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
        <h2 className="text-sm font-bold text-white mb-4">Generated PDF Reports Archive</h2>

        {reports.length === 0 ? (
          <div className="py-12 text-center text-gray-500 text-sm">
            <FileText className="w-8 h-8 mx-auto mb-2 text-gray-600" />
            No reports generated yet.<br />
            Click "Generate Official PDF Report" to compile a new audit report.
          </div>
        ) : (
          <div className="overflow-x-auto rounded-lg border border-gray-800">
            <table className="w-full text-xs">
              <thead className="bg-gray-800 text-gray-400">
                <tr>
                  <th className="py-3 px-4 text-left">Report ID</th>
                  <th className="py-3 px-4 text-left">Document File</th>
                  <th className="py-3 px-4 text-left">Format</th>
                  <th className="py-3 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-800 text-gray-300">
                {reports.map((r) => (
                  <tr key={r.report_id} className="hover:bg-gray-800/40">
                    <td className="py-3 px-4 font-mono font-medium text-white">{r.report_id}</td>
                    <td className="py-3 px-4 text-gray-300">{r.filename}</td>
                    <td className="py-3 px-4">
                      <span className="px-2 py-0.5 rounded text-[11px] font-bold bg-red-950 text-red-300 border border-red-800">
                        PDF
                      </span>
                    </td>
                    <td className="py-3 px-4 text-right">
                      <button
                        onClick={() => handleDownload(r.download_url)}
                        className="inline-flex items-center gap-1 px-3 py-1 bg-gray-800 hover:bg-gray-700 rounded text-xs text-gray-200 transition-colors"
                      >
                        <Download className="w-3 h-3 text-emerald-400" /> Download
                      </button>
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
