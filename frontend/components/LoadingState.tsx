export function LoadingState() {
  return (
    <div className="space-y-4">
      <div className="h-8 bg-slate-200 rounded w-1/4 animate-pulse" />
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {[1, 2, 3, 4].map((i) => (
          <div key={i} className="bg-white border border-slate-200 rounded-lg p-6 space-y-3">
            <div className="h-4 bg-slate-200 rounded w-3/4 animate-pulse" />
            <div className="h-8 bg-slate-200 rounded w-1/2 animate-pulse" />
            <div className="h-3 bg-slate-100 rounded w-full animate-pulse" />
          </div>
        ))}
      </div>
    </div>
  )
}
