'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { useAuth } from '@/lib/AuthContext'
import { mockLogin, setToken, setUser } from '@/lib/auth'

export default function LoginPage() {
  const router = useRouter()
  const { isAuthenticated, isLoading } = useAuth()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)

  // Redirect if already authenticated (check after loading)
  useEffect(() => {
    if (!isLoading && isAuthenticated) {
      router.push('/')
    }
  }, [isAuthenticated, isLoading, router])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setIsSubmitting(true)

    try {
      const response = await mockLogin(email, password)
      setToken(response.access_token)
      setUser(response.user)

      // Force redirect to dashboard
      router.push('/')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Login failed')
      setIsSubmitting(false)
    }
  }

  // Show loading state while checking auth
  if (isLoading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-900 to-slate-800 flex items-center justify-center">
        <div className="text-white text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-white mx-auto mb-4"></div>
          <p>Loading...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 to-slate-800 flex items-center justify-center px-4">
      <div className="w-full max-w-md">
        {/* Logo and Branding */}
        <div className="text-center mb-8">
          <div className="w-16 h-16 bg-blue-500 rounded-lg flex items-center justify-center font-bold text-2xl text-white mx-auto mb-4">
            📦
          </div>
          <h1 className="text-3xl font-bold text-white mb-2">IntelliStock Agent</h1>
          <p className="text-slate-300">AI-Powered Inventory Intelligence</p>
        </div>

        {/* Login Form */}
        <form onSubmit={handleSubmit} className="bg-white rounded-lg shadow-xl p-8 space-y-6">
          <h2 className="text-2xl font-bold text-slate-900 text-center">Welcome Back</h2>

          {/* Error Message */}
          {error && (
            <div className="bg-red-50 border border-red-200 rounded-lg p-4">
              <p className="text-sm text-red-800">{error}</p>
            </div>
          )}

          {/* Email Field */}
          <div>
            <label htmlFor="email" className="block text-sm font-medium text-slate-700 mb-2">
              Email Address
            </label>
            <input
              id="email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="umerusman563@gmail.com"
              className="w-full px-4 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              required
              disabled={isSubmitting}
            />
          </div>

          {/* Password Field */}
          <div>
            <label htmlFor="password" className="block text-sm font-medium text-slate-700 mb-2">
              Password
            </label>
            <input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
              className="w-full px-4 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              required
              disabled={isSubmitting}
            />
          </div>

          {/* Submit Button */}
          <button
            type="submit"
            disabled={isSubmitting}
            className="w-full bg-blue-600 text-white py-2 rounded-lg font-semibold hover:bg-blue-700 disabled:bg-slate-400 disabled:cursor-not-allowed transition-colors"
          >
            {isSubmitting ? 'Signing in...' : 'Sign In'}
          </button>

          {/* Register Link */}
          <div className="text-center pt-4 border-t border-slate-200">
            <p className="text-slate-600 text-sm">
              Don't have an account?{' '}
              <Link href="/register" className="text-blue-600 font-semibold hover:text-blue-700">
                Register here
              </Link>
            </p>
          </div>
        </form>

        {/* Development Info */}
        <div className="mt-8 bg-slate-800 border border-slate-700 rounded-lg p-4 space-y-3">
          <div>
            <p className="text-xs text-slate-300 font-semibold mb-2">✨ Getting Started</p>
            <p className="text-xs text-slate-400">
              Don't have an account? Go to <Link href="/register" className="text-blue-400 hover:text-blue-300 underline">Register</Link> to create one with your custom password!
            </p>
          </div>
          <div>
            <p className="text-xs text-slate-300 font-semibold mb-2">📝 Default Demo Accounts</p>
            <div className="space-y-1 text-xs text-slate-500">
              <p className="font-mono bg-slate-900 px-2 py-1 rounded">
                umerusman563@gmail.com / admin123 (Admin)
              </p>
              <p className="font-mono bg-slate-900 px-2 py-1 rounded">
                umerusman563@gmail.com / user123 (User)
              </p>
            </div>
          </div>
          <p className="text-xs text-slate-500">⚠️ Phase 5 will replace this with real JWT authentication</p>
        </div>
      </div>
    </div>
  )
}
