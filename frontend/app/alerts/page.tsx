'use client'

import { PageHeader } from '@/components/PageHeader'
import { EmptyState } from '@/components/EmptyState'

export default function Alerts() {
  return (
    <div className="space-y-8">
      <PageHeader
        title="Alerts & Notifications"
        description="Monitor stock-out and low-stock events"
        icon="🔔"
        action={
          <button className="bg-blue-600 text-white px-4 py-2 rounded-lg font-medium hover:bg-blue-700">
            Alert Settings
          </button>
        }
      />

      <div className="flex gap-4">
        <button className="px-4 py-2 bg-white border border-slate-300 rounded-lg font-medium hover:bg-slate-50">
          All Alerts
        </button>
        <button className="px-4 py-2 bg-white border border-slate-300 rounded-lg font-medium hover:bg-slate-50">
          Critical
        </button>
        <button className="px-4 py-2 bg-white border border-slate-300 rounded-lg font-medium hover:bg-slate-50">
          Resolved
        </button>
      </div>

      <EmptyState
        title="No alerts yet"
        description="Alerts will appear here when stock levels change or inventory anomalies are detected."
        icon="📬"
      />

      {/* Alert Timeline Preview */}
      <div className="bg-white border border-slate-200 rounded-lg p-6">
        <h3 className="font-semibold text-slate-900 mb-4">Alert Timeline</h3>
        <div className="space-y-4">
          {[1, 2, 3].map((i) => (
            <div key={i} className="flex gap-4 pb-4 border-b border-slate-100 last:border-0">
              <div className="w-3 h-3 rounded-full bg-slate-300 mt-1.5 flex-shrink-0" />
              <div className="flex-1">
                <p className="text-sm font-medium text-slate-900">Alert placeholder {i}</p>
                <p className="text-xs text-slate-500 mt-1">Alerts will be populated once reconciliation is active</p>
              </div>
              <span className="text-xs text-slate-400 whitespace-nowrap">--:--:--</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
