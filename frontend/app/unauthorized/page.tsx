'use client'

import Link from 'next/link'
import { useAuth } from '@/lib/AuthContext'

export default function UnauthorizedPage() {
  const { user } = useAuth()

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 to-slate-800 flex items-center justify-center px-4">
      <div className="text-center">
        <div className="text-6xl mb-4">🔒</div>
        <h1 className="text-4xl font-bold text-white mb-2">Access Denied</h1>
        <p className="text-slate-300 mb-8">
          Your account ({user?.email}) does not have permission to access this resource.
        </p>

        <div className="space-y-4">
          <Link
            href="/"
            className="inline-block bg-blue-600 text-white px-6 py-3 rounded-lg font-semibold hover:bg-blue-700"
          >
            Return to Dashboard
          </Link>
          <div>
            <p className="text-slate-400 text-sm">
              If you believe this is an error, contact your system administrator.
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}
