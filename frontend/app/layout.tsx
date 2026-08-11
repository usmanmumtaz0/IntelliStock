import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: 'IntelliStock Agent',
  description: 'AI-powered inventory intelligence platform',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body>
        <div className="min-h-screen flex flex-col">
          <nav className="bg-slate-900 text-white p-4 border-b border-slate-700">
            <div className="max-w-7xl mx-auto flex items-center justify-between">
              <h1 className="text-2xl font-bold">IntelliStock Agent</h1>
              <div className="flex gap-6">
                <a href="/" className="hover:text-blue-400">Dashboard</a>
                <a href="/shelves" className="hover:text-blue-400">Shelves</a>
                <a href="/inventory" className="hover:text-blue-400">Inventory</a>
                <a href="/alerts" className="hover:text-blue-400">Alerts</a>
                <a href="/settings" className="hover:text-blue-400">Settings</a>
              </div>
            </div>
          </nav>
          <main className="flex-1 max-w-7xl mx-auto w-full p-6">
            {children}
          </main>
        </div>
      </body>
    </html>
  )
}
