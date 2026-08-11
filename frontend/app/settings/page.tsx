'use client'

import { PageHeader } from '@/components/PageHeader'
import { ProtectedRoute } from '@/lib/ProtectedRoute'

function SettingsContent() {
  return (
    <div className="space-y-8">
      <PageHeader
        title="Settings"
        description="Configure system preferences and thresholds"
        icon="⚙️"
      />

      <div className="space-y-6">
        {/* API Configuration */}
        <SettingsSection
          title="API Configuration"
          description="Backend service connection"
        >
          <SettingField
            label="API URL"
            value={process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'}
            readOnly
          />
          <ConnectionStatus />
        </SettingsSection>

        {/* Inventory Thresholds */}
        <SettingsSection
          title="Inventory Thresholds"
          description="Configure low-stock and reorder thresholds"
        >
          <SettingField label="Low Stock Threshold (%)" value="20" placeholder="20" />
          <SettingField label="Reorder Point (units)" value="50" placeholder="50" />
          <SettingField label="Reconciliation Confidence (min)" value="0.75" placeholder="0.75" />
        </SettingsSection>

        {/* Notification Preferences */}
        <SettingsSection
          title="Notifications"
          description="Configure alert and notification settings"
        >
          <CheckboxField label="Email alerts on low stock" defaultChecked={false} />
          <CheckboxField label="WebSocket real-time updates" defaultChecked={true} />
          <CheckboxField label="Daily inventory report" defaultChecked={false} />
        </SettingsSection>

        {/* System Info */}
        <SettingsSection title="System Information" description="Technical details">
          <SettingField label="Frontend Version" value="0.1.0" readOnly />
          <SettingField label="Environment" value="development" readOnly />
        </SettingsSection>

        {/* Actions */}
        <div className="flex gap-4 pt-6">
          <button className="px-6 py-2 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700">
            Save Settings
          </button>
          <button className="px-6 py-2 bg-white border border-slate-300 rounded-lg font-medium hover:bg-slate-50">
            Reset to Defaults
          </button>
        </div>
      </div>
    </div>
  )
}

export default function Settings() {
  return (
    <ProtectedRoute>
      <SettingsContent />
    </ProtectedRoute>
  )
}

function SettingsSection({
  title,
  description,
  children,
}: {
  title: string
  description: string
  children: React.ReactNode
}) {
  return (
    <div className="bg-white border border-slate-200 rounded-lg p-6">
      <h3 className="font-semibold text-slate-900 mb-1">{title}</h3>
      <p className="text-sm text-slate-600 mb-4">{description}</p>
      <div className="space-y-4">{children}</div>
    </div>
  )
}

function SettingField({
  label,
  value,
  placeholder,
  readOnly,
}: {
  label: string
  value: string
  placeholder?: string
  readOnly?: boolean
}) {
  return (
    <div>
      <label className="block text-sm font-medium text-slate-700 mb-1">{label}</label>
      <input
        type="text"
        defaultValue={value}
        placeholder={placeholder}
        readOnly={readOnly}
        className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-slate-100 disabled:text-slate-500"
        disabled={readOnly}
      />
    </div>
  )
}

function CheckboxField({ label, defaultChecked }: { label: string; defaultChecked: boolean }) {
  return (
    <label className="flex items-center gap-2 cursor-pointer">
      <input
        type="checkbox"
        defaultChecked={defaultChecked}
        className="w-4 h-4 rounded border border-slate-300 text-blue-600 focus:ring-2 focus:ring-blue-500"
      />
      <span className="text-sm text-slate-700">{label}</span>
    </label>
  )
}

function ConnectionStatus() {
  return (
    <div className="mt-3 flex items-center gap-2">
      <div className="w-3 h-3 rounded-full bg-green-500" />
      <span className="text-sm text-slate-600">Connected to backend</span>
    </div>
  )
}
