import { createContext, useContext, useEffect, useState, type ReactNode } from 'react'
import { currentUser, login, logout, register, type Signup, type User } from './api'

type Auth = {
  user: User | null
  loading: boolean
  error: string
  refresh: () => Promise<void>
  signIn: (email: string, password: string) => Promise<void>
  signUp: (data: Signup) => Promise<void>
  signOut: () => Promise<void>
}
const AuthContext = createContext<Auth | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  async function refresh() {
    setLoading(true); setError('')
    try { setUser(await currentUser()) }
    catch (e) { setError(e instanceof Error ? e.message : 'Unable to check your account.') }
    finally { setLoading(false) }
  }
  useEffect(() => { void refresh() }, [])
  // Revalidate when returning to a tab: another tab may have logged out.
  useEffect(() => {
    const onFocus = () => { void refresh() }
    window.addEventListener('focus', onFocus)
    return () => window.removeEventListener('focus', onFocus)
  }, [])
  return <AuthContext.Provider value={{ user, loading, error, refresh,
    signIn: async (email, password) => { setUser(await login(email, password)); setError('') },
    signUp: async data => { setUser(await register(data)); setError('') },
    signOut: async () => { await logout(); setUser(null); setError('') },
  }}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const auth = useContext(AuthContext)
  if (!auth) throw new Error('Authentication provider is missing')
  return auth
}
