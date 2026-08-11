interface PageHeaderProps {
  title: string
  description?: string
  icon?: string
  action?: React.ReactNode
}

export function PageHeader({ title, description, icon, action }: PageHeaderProps) {
  return (
    <div className="mb-8 flex items-center justify-between">
      <div className="flex items-center gap-3">
        {icon && <span className="text-4xl">{icon}</span>}
        <div>
          <h1 className="text-4xl font-bold text-slate-900">{title}</h1>
          {description && <p className="text-slate-600 mt-1">{description}</p>}
        </div>
      </div>
      {action && <div>{action}</div>}
    </div>
  )
}
