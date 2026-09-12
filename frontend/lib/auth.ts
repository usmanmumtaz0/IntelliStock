/**
 * Authentication utilities for token management.
 * Note: For production, use secure httpOnly cookies instead of localStorage.
 */

const TOKEN_KEY = 'intellistock_token'
const USER_KEY = 'intellistock_user'

export interface User {
  id: string
  email: string
  username: string
  role: 'admin' | 'user' | 'viewer'
}

export interface AuthResponse {
  access_token: string
  token_type: string
  user: User
}

/**
 * Store JWT token in localStorage
 */
export function setToken(token: string): void {
  if (typeof window !== 'undefined') {
    localStorage.setItem(TOKEN_KEY, token)
  }
}

/**
 * Retrieve JWT token from localStorage
 */
export function getToken(): string | null {
  if (typeof window !== 'undefined') {
    return localStorage.getItem(TOKEN_KEY)
  }
  return null
}

/**
 * Store user info in localStorage
 */
export function setUser(user: User): void {
  if (typeof window !== 'undefined') {
    localStorage.setItem(USER_KEY, JSON.stringify(user))
  }
}

/**
 * Retrieve user info from localStorage
 */
export function getUser(): User | null {
  if (typeof window !== 'undefined') {
    const user = localStorage.getItem(USER_KEY)
    return user ? JSON.parse(user) : null
  }
  return null
}

/**
 * Check if user is authenticated
 */
export function isAuthenticated(): boolean {
  return getToken() !== null
}

/**
 * Clear auth tokens and user info
 */
export function clearAuth(): void {
  if (typeof window !== 'undefined') {
    localStorage.removeItem(TOKEN_KEY)
    localStorage.removeItem(USER_KEY)
  }
}

/**
 * Mock login for development (Phase 5 will implement real JWT)
 */
export async function mockLogin(email: string, password: string): Promise<AuthResponse> {
  // Simulate network delay
  await new Promise((resolve) => setTimeout(resolve, 500))

  // Mock users for development
  // Admin: umerusman563@gmail.com / admin123
  if (email === 'umerusman563@gmail.com' && password === 'admin123') {
    return {
      access_token: 'mock_token_admin_' + Date.now(),
      token_type: 'bearer',
      user: {
        id: '1',
        email: 'umerusman563@gmail.com',
        username: 'admin',
        role: 'admin',
      },
    }
  }

  // User: umerusman563@gmail.com / user123
  if (email === 'umerusman563@gmail.com' && password === 'user123') {
    return {
      access_token: 'mock_token_user_' + Date.now(),
      token_type: 'bearer',
      user: {
        id: '2',
        email: 'umerusman563@gmail.com',
        username: 'user',
        role: 'user',
      },
    }
  }

  // Also support legacy test accounts
  if (email === 'admin@intellistock.local' && password === 'admin123') {
    return {
      access_token: 'mock_token_admin_' + Date.now(),
      token_type: 'bearer',
      user: {
        id: '1',
        email: 'admin@intellistock.local',
        username: 'admin',
        role: 'admin',
      },
    }
  }

  if (email === 'user@intellistock.local' && password === 'user123') {
    return {
      access_token: 'mock_token_user_' + Date.now(),
      token_type: 'bearer',
      user: {
        id: '2',
        email: 'user@intellistock.local',
        username: 'user',
        role: 'user',
      },
    }
  }

  throw new Error('Invalid credentials')
}

/**
 * Mock register for development (Phase 5 will implement real registration)
 */
export async function mockRegister(
  email: string,
  username: string,
  password: string
): Promise<AuthResponse> {
  // Simulate network delay
  await new Promise((resolve) => setTimeout(resolve, 500))

  // Simple validation
  if (!email.includes('@') || password.length < 6) {
    throw new Error('Invalid email or password too short')
  }

  return {
    access_token: 'mock_token_' + Date.now(),
    token_type: 'bearer',
    user: {
      id: Date.now().toString(),
      email,
      username,
      role: 'user',
    },
  }
}
