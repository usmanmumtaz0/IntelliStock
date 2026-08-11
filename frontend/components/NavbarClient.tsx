'use client'

import { useState } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { useAuth } from '@/lib/AuthContext'

export function NavbarClient() {
  const router = useRouter()
  const { user, isAuthenticated, logout } = useAuth()
  const [showMenu, setShowMenu] = useState(false)

  if (!isAuthenticated || !user) {
    return (
      <Link
        href="/login"
        className="text-slate-300 hover:text-white font-medium transition-colors"
      >
        Sign In
      </Link>
    )
  }

  const handleLogout = () => {
    logout()
    setShowMenu(false)
    router.push('/login')
  }

  return (
    <div className="relative">
      <button
        onClick={() => setShowMenu(!showMenu)}
        className="flex items-center gap-2 text-slate-300 hover:text-white transition-colors"
      >
        <span className="text-sm">{user.username}</span>
        <div className="w-8 h-8 rounded-full bg-blue-500 flex items-center justify-center text-xs font-bold">
          {user.username[0].toUpperCase()}
        </div>
      </button>

      {showMenu && (
        <div className="absolute right-0 mt-2 w-48 bg-slate-800 rounded-lg shadow-xl border border-slate-700 z-50">
          <div className="px-4 py-3 border-b border-slate-700">
            <p className="text-sm text-slate-300">{user.email}</p>
            <p className="text-xs text-slate-500 capitalize">{user.role}</p>
          </div>
          <div className="py-2">
            <button
              onClick={handleLogout}
              className="w-full text-left px-4 py-2 text-sm text-slate-300 hover:bg-slate-700 hover:text-white transition-colors"
            >
              Sign Out
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
