'use client'

import { createContext, useContext, useEffect, useState, ReactNode } from 'react'
import { User, getToken, getUser, isAuthenticated, clearAuth } from './auth'

interface AuthContextType {
  user: User | null
  isLoading: boolean
  isAuthenticated: boolean
  logout: () => void
  refreshAuth: () => void
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  const refreshAuth = () => {
    const storedUser = getUser()
    const token = getToken()

    if (storedUser && token) {
      setUser(storedUser)
    } else {
      setUser(null)
    }
  }

  // Initialize auth state from localStorage on mount
  useEffect(() => {
    refreshAuth()
    setIsLoading(false)

    // Listen for storage changes (e.g., login from another tab)
    const handleStorageChange = () => {
      refreshAuth()
    }

    window.addEventListener('storage', handleStorageChange)
    return () => window.removeEventListener('storage', handleStorageChange)
  }, [])

  const logout = () => {
    clearAuth()
    setUser(null)
  }

  const value: AuthContextType = {
    user,
    isLoading,
    isAuthenticated: user !== null,
    logout,
    refreshAuth,
  }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}
