import {
  createContext,
  useContext,
  useState,
  useCallback,
  useEffect,
  type ReactNode,
} from "react"
import { apiFetch, getAuthToken, setAuthToken, clearAuthToken } from "@/lib/httpClient"

type User = {
  id: string
  first_name: string
  last_name: string
  email: string
}

type AuthContextType = {
  user: User | null
  isLoading: boolean
  login: (email: string) => Promise<void>
  logout: () => Promise<void>
  error: string | null
}

const AuthContext = createContext<AuthContextType | null>(null)

async function fetchCurrentUser(): Promise<User> {
  const res = await apiFetch("/api/auth/me")
  if (!res.ok) throw new Error("Failed to fetch user")
  return res.json()
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const token = getAuthToken()
    if (token) {
      fetchCurrentUser()
        .then(setUser)
        .catch(() => {
          clearAuthToken()
          setUser(null)
        })
        .finally(() => setIsLoading(false))
    } else {
      setIsLoading(false)
    }
  }, [])

  const login = useCallback(async (email: string) => {
    setError(null)
    const res = await apiFetch("/api/auth/login", {
      method: "POST",
      body: JSON.stringify({ email }),
    })

    if (!res.ok) {
      const data = await res.json()
      setError(data.detail || "ログインに失敗しました")
      throw new Error(data.detail)
    }

    const data = await res.json()
    setAuthToken(data.token)
    setUser(data.user)
  }, [])

  const logout = useCallback(async () => {
    clearAuthToken()
    setUser(null)
    setError(null)
  }, [])

  return (
    <AuthContext.Provider value={{ user, isLoading, login, logout, error }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error("useAuth must be used within AuthProvider")
  }
  return context
}
