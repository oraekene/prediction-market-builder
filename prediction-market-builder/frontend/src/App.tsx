import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider } from '@/contexts/AuthContext'
import MainLayout from '@/components/layout/MainLayout'
import ChatInterface from '@/components/chat/ChatInterface'
import MarketsPage from '@/pages/MarketsPage'
import StrategiesPage from '@/pages/StrategiesPage'
import AnalyticsPage from '@/pages/AnalyticsPage'
import SettingsPage from '@/pages/SettingsPage'
import ResearchPage from '@/pages/ResearchPage'
import PaperTradingPage from '@/pages/PaperTradingPage'
import LoginPage from '@/pages/LoginPage'
import ProtectedRoute from '@/components/auth/ProtectedRoute'
import MetaStrategiesPage from '@/pages/MetaStrategiesPage'

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route element={<ProtectedRoute><MainLayout /></ProtectedRoute>}>
            <Route path="/" element={<Navigate to="/markets" replace />} />
            <Route path="/markets" element={<MarketsPage />} />
            <Route path="/strategies" element={<StrategiesPage />} />
            <Route path="/analytics" element={<AnalyticsPage />} />
            <Route path="/settings" element={<SettingsPage />} />
            <Route path="/research" element={<ResearchPage />} />
            <Route path="/paper-trading" element={<PaperTradingPage />} />
            <Route path="/meta-strategies" element={<MetaStrategiesPage />} />
            <Route path="/meta-strategies/:id" element={<MetaStrategiesPage />} />
          </Route>
        </Routes>
        <ChatInterface />
      </BrowserRouter>
    </AuthProvider>
  )
}
