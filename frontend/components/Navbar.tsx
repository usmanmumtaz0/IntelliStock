import Link from 'next/link'

export function Navbar() {
  return (
    <nav className="bg-slate-900 text-white border-b border-slate-700 sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 py-4 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 bg-blue-500 rounded flex items-center justify-center font-bold">
            📦
          </div>
          <h1 className="text-2xl font-bold">IntelliStock Agent</h1>
        </div>
        
        <div className="flex gap-8">
          <NavLink href="/" label="Dashboard" />
          <NavLink href="/shelves" label="Shelves" />
          <NavLink href="/inventory" label="Inventory" />
          <NavLink href="/alerts" label="Alerts" />
          <NavLink href="/settings" label="Settings" />
        </div>
      </div>
    </nav>
  )
}

function NavLink({ href, label }: { href: string; label: string }) {
  return (
    <Link
      href={href}
      className="text-slate-300 hover:text-white transition-colors font-medium"
    >
      {label}
    </Link>
  )
}
