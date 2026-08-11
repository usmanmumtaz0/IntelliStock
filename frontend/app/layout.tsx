import type { Metadata } from 'next'
import { Navbar } from '@/components/Navbar'
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
        <div className="min-h-screen flex flex-col bg-slate-50">
          <Navbar />
          <main className="flex-1 max-w-7xl mx-auto w-full px-6 py-8">
            {children}
          </main>
        </div>
      </body>
    </html>
  )
}
