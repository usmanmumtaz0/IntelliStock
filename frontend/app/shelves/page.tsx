'use client'

import { PageHeader } from '@/components/PageHeader'
import { EmptyState } from '@/components/EmptyState'

export default function Shelves() {
  return (
    <div className="space-y-8">
      <PageHeader
        title="Shelves & Zones"
        description="Configure camera zones and shelf boundaries"
        icon="📦"
        action={
          <button className="bg-blue-600 text-white px-4 py-2 rounded-lg font-medium hover:bg-blue-700">
            Add Camera Zone
          </button>
        }
      />

      <EmptyState
        title="No shelves configured yet"
        description="Add your first camera and define shelf zones to start monitoring inventory."
        icon="🎥"
      />

      {/* Zone Configuration Help */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-6">
        <h3 className="font-semibold text-blue-900 mb-2">Getting Started</h3>
        <ul className="text-sm text-blue-800 space-y-2 list-disc list-inside">
          <li>Add a camera in Phase 5 (Backend API)</li>
          <li>Define ROI polygons for each shelf zone</li>
          <li>Calibrate with known product counts</li>
          <li>Enable monitoring</li>
        </ul>
      </div>
    </div>
  )
}
