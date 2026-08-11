'use client'

import { PageHeader } from '@/components/PageHeader'
import { EmptyState } from '@/components/EmptyState'
import { ProtectedRoute } from '@/lib/ProtectedRoute'

function InventoryContent() {
  return (
    <div className="space-y-8">
      <PageHeader
        title="Inventory"
        description="View current inventory state across all zones"
        icon="📊"
      />

      <div className="flex gap-4 mb-6">
        <input
          type="text"
          placeholder="Search products..."
          className="flex-1 px-4 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
        <select className="px-4 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500">
          <option>All Status</option>
          <option>Adequate Stock</option>
          <option>Low Stock</option>
          <option>Out of Stock</option>
          <option>Uncertain</option>
        </select>
      </div>

      <EmptyState
        title="No inventory data available"
        description="Once cameras are configured and monitoring starts in Phase 3, inventory will be displayed here."
        icon="📦"
      />

      {/* Table Structure Preview */}
      <div className="bg-white border border-slate-200 rounded-lg overflow-hidden">
        <table className="w-full">
          <thead className="bg-slate-50 border-b border-slate-200">
            <tr>
              <th className="px-6 py-3 text-left text-sm font-semibold text-slate-900">Product</th>
              <th className="px-6 py-3 text-left text-sm font-semibold text-slate-900">Zone</th>
              <th className="px-6 py-3 text-left text-sm font-semibold text-slate-900">Quantity</th>
              <th className="px-6 py-3 text-left text-sm font-semibold text-slate-900">Status</th>
              <th className="px-6 py-3 text-left text-sm font-semibold text-slate-900">Last Updated</th>
            </tr>
          </thead>
          <tbody>
            <tr className="border-b border-slate-100">
              <td colSpan={5} className="px-6 py-8 text-center text-slate-500">
                No inventory records
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  )
}

export default function Inventory() {
  return (
    <ProtectedRoute>
      <InventoryContent />
    </ProtectedRoute>
  )
}
