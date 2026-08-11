interface EmptyStateProps {
  title: string
  description: string
  icon?: string
}

export function EmptyState({ title, description, icon = '📭' }: EmptyStateProps) {
  return (
    <div className="bg-white border border-slate-200 rounded-lg p-12 text-center">
      <div className="text-5xl mb-4">{icon}</div>
      <h3 className="text-xl font-semibold text-slate-900 mb-2">{title}</h3>
      <p className="text-slate-600">{description}</p>
    </div>
  )
}
