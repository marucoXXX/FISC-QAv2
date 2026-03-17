import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom"
import { AuthProvider, useAuth } from "@/hooks/useAuth"
import { Layout } from "@/components/layout"
import LoginPage from "@/pages/LoginPage"

function PrivateRoute({ children }: { children: React.ReactNode }) {
  const { user, isLoading } = useAuth()

  if (isLoading) {
    return null
  }

  if (!user) {
    return <Navigate to="/login" replace />
  }

  return <>{children}</>
}

function WelcomePage() {
  return (
    <div className="flex items-center justify-center h-64">
      <p className="text-2xl text-muted-foreground">Welcome</p>
    </div>
  )
}

function AppRoutes() {
  const { user, isLoading } = useAuth()

  if (isLoading) return null

  return (
    <Routes>
      <Route path="/login" element={user ? <Navigate to="/welcome" /> : <LoginPage />} />
      <Route path="/" element={<Navigate to="/welcome" />} />
      <Route
        path="/welcome"
        element={
          <PrivateRoute>
            <Layout title="Welcome">
              <WelcomePage />
            </Layout>
          </PrivateRoute>
        }
      />
    </Routes>
  )
}

function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <AppRoutes />
      </AuthProvider>
    </BrowserRouter>
  )
}

export default App
