import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom"
import { AuthProvider, useAuth } from "@/hooks/useAuth"
import { Layout } from "@/components/layout"
import LoginPage from "@/pages/LoginPage"
import BankListPage from "@/pages/BankListPage"
import BankDetailPage from "@/pages/BankDetailPage"
import CommonAnswersPage from "@/pages/CommonAnswersPage"
import SessionListPage from "@/pages/SessionListPage"
import SessionNewPage from "@/pages/SessionNewPage"
import SessionStep2Page from "@/pages/SessionStep2Page"
import SessionStep3Page from "@/pages/SessionStep3Page"
import SessionStep4Page from "@/pages/SessionStep4Page"
import SessionStep5Page from "@/pages/SessionStep5Page"

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

function P({ children, title }: { children: React.ReactNode; title: string }) {
  return (
    <PrivateRoute>
      <Layout title={title}>{children}</Layout>
    </PrivateRoute>
  )
}

function AppRoutes() {
  const { user, isLoading } = useAuth()

  if (isLoading) return null

  return (
    <Routes>
      <Route path="/login" element={user ? <Navigate to="/banks" /> : <LoginPage />} />
      <Route path="/" element={<Navigate to="/banks" />} />
      <Route path="/welcome" element={<P title="Welcome"><WelcomePage /></P>} />
      <Route path="/banks" element={<P title="銀行管理"><BankListPage /></P>} />
      <Route path="/banks/:bankId" element={<P title="銀行詳細"><BankDetailPage /></P>} />
      <Route path="/common-answers" element={<P title="共通回答DB"><CommonAnswersPage /></P>} />
      <Route path="/sessions" element={<P title="セッション"><SessionListPage /></P>} />
      <Route path="/sessions/new" element={<P title="新規セッション"><SessionNewPage /></P>} />
      <Route path="/sessions/:sessionId/step2" element={<P title="過去回答マッチング"><SessionStep2Page /></P>} />
      <Route path="/sessions/:sessionId/step3" element={<P title="共通回答マッチング"><SessionStep3Page /></P>} />
      <Route path="/sessions/:sessionId/step4" element={<P title="AI回答生成"><SessionStep4Page /></P>} />
      <Route path="/sessions/:sessionId/step5" element={<P title="最終確認"><SessionStep5Page /></P>} />
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
