/**
 * Authentication utilities for token management.
 * Note: For production, use secure httpOnly cookies instead of localStorage.
 */

const TOKEN_KEY = 'intellistock_token'
const USER_KEY = 'intellistock_user'
const USERS_DB_KEY = 'intellistock_users_db'

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

// Initialize mock users database in localStorage
function initializeUsersDB() {
  if (typeof window !== 'undefined') {
    const existing = localStorage.getItem(USERS_DB_KEY)
    if (!existing) {
      const defaultUsers = {
        'umerusman563@gmail.com_admin': {
          email: 'umerusman563@gmail.com',
          password: 'admin123',
          username: 'admin',
          role: 'admin',
        },
        'umerusman563@gmail.com_user': {
          email: 'umerusman563@gmail.com',
          password: 'user123',
          username: 'user',
          role: 'user',
        },
      }
      localStorage.setItem(USERS_DB_KEY, JSON.stringify(defaultUsers))
    }
  }
}

// Get all registered users
function getUsersDB(): Record<string, any> {
  if (typeof window === 'undefined') return {}
  initializeUsersDB()
  const db = localStorage.getItem(USERS_DB_KEY)
  return db ? JSON.parse(db) : {}
}

// Save updated users database
function saveUsersDB(users: Record<string, any>) {
  if (typeof window !== 'undefined') {
    localStorage.setItem(USERS_DB_KEY, JSON.stringify(users))
  }
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

  initializeUsersDB()
  const usersDB = getUsersDB()

  // Find user by email and password
  for (const [key, userRecord] of Object.entries(usersDB)) {
    const user = userRecord as any
    if (user.email === email && user.password === password) {
      return {
        access_token: 'mock_token_' + Date.now(),
        token_type: 'bearer',
        user: {
          id: user.email + '_' + user.role,
          email: user.email,
          username: user.username,
          role: user.role,
        },
      }
    }
  }

  throw new Error('Invalid credentials')
}

/**
 * Mock register for development - creates a new user or updates existing
 */
export async function mockRegister(
  email: string,
  username: string,
  password: string,
  role: 'admin' | 'user' | 'viewer' = 'user'
): Promise<AuthResponse> {
  // Simulate network delay
  await new Promise((resolve) => setTimeout(resolve, 500))

  // Simple validation
  if (!email.includes('@')) {
    throw new Error('Invalid email format')
  }
  if (password.length < 6) {
    throw new Error('Password must be at least 6 characters')
  }
  if (username.length < 3) {
    throw new Error('Username must be at least 3 characters')
  }

  initializeUsersDB()
  const usersDB = getUsersDB()

  // Create user key (email + role combination for uniqueness)
  const userKey = email + '_' + role

  // Store or update user
  usersDB[userKey] = {
    email,
    password,
    username,
    role,
  }

  saveUsersDB(usersDB)

  return {
    access_token: 'mock_token_' + Date.now(),
    token_type: 'bearer',
    user: {
      id: userKey,
      email,
      username,
      role,
    },
  }
}
