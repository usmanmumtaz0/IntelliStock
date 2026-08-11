'use client'

import { PageHeader } from '@/components/PageHeader'
import { ProtectedRoute } from '@/lib/ProtectedRoute'

function DashboardContent() {
  return (
    <div className="space-y-8">
      <PageHeader
        title="Dashboard"
        description="Real-time inventory monitoring and alerts"
        icon="📊"
      />

      {/* Status Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatusCard label="Total Products" value="—" status="loading" />
        <StatusCard label="Cameras Online" value="—" status="loading" />
        <StatusCard label="Low Stock Alerts" value="—" status="loading" />
        <StatusCard label="Last Updated" value="—" status="loading" />
      </div>

      {/* Charts and Data */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <ChartPlaceholder title="Inventory Trend" />
        <ChartPlaceholder title="Alert Timeline" />
      </div>

      {/* Recent Activity */}
      <RecentActivityPlaceholder />
    </div>
  )
}

export default function Dashboard() {
  return (
    <ProtectedRoute>
      <DashboardContent />
    </ProtectedRoute>
  )
}

function StatusCard({
  label,
  value,
  status,
}: {
  label: string
  value: string
  status: 'loading' | 'ok' | 'warning' | 'error'
}) {
  const statusColors = {
    loading: 'bg-slate-100 text-slate-600',
    ok: 'bg-green-100 text-green-700',
    warning: 'bg-yellow-100 text-yellow-700',
    error: 'bg-red-100 text-red-700',
  }

  return (
    <div className="bg-white border border-slate-200 rounded-lg p-6">
      <p className="text-sm font-medium text-slate-600 mb-2">{label}</p>
      <p className="text-3xl font-bold text-slate-900 mb-3">{value}</p>
      <div className={`inline-block px-3 py-1 rounded text-xs font-semibold ${statusColors[status]}`}>
        {status === 'loading' ? 'Loading...' : status.toUpperCase()}
      </div>
    </div>
  )
}

function ChartPlaceholder({ title }: { title: string }) {
  return (
    <div className="bg-white border border-slate-200 rounded-lg p-6">
      <h3 className="font-semibold text-slate-900 mb-4">{title}</h3>
      <div className="h-64 bg-slate-50 rounded flex items-center justify-center border border-dashed border-slate-300">
        <div className="text-center">
          <p className="text-slate-400 text-sm">Chart placeholder</p>
          <p className="text-slate-500 text-xs mt-1">Data will appear in Phase 6</p>
        </div>
      </div>
    </div>
  )
}

function RecentActivityPlaceholder() {
  return (
    <div className="bg-white border border-slate-200 rounded-lg p-6">
      <h3 className="font-semibold text-slate-900 mb-4">Recent Activity</h3>
      <div className="space-y-3">
        {[1, 2, 3].map((i) => (
          <div key={i} className="flex items-center justify-between py-3 border-b border-slate-100 last:border-0">
            <div className="flex items-center gap-3">
              <div className="w-2 h-2 rounded-full bg-slate-300" />
              <div>
                <p className="text-sm font-medium text-slate-900">Activity item {i}</p>
                <p className="text-xs text-slate-500">Placeholder for real-time events</p>
              </div>
            </div>
            <span className="text-xs text-slate-400">--:--</span>
          </div>
        ))}
      </div>
    </div>
  )
}
