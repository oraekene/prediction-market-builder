import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import MainLayout from '@/components/layout/MainLayout'
import ChatInterface from '@/components/chat/ChatInterface'
import MarketsPage from '@/pages/MarketsPage'
import StrategiesPage from '@/pages/StrategiesPage'
import AnalyticsPage from '@/pages/AnalyticsPage'
import SettingsPage from '@/pages/SettingsPage'
import ResearchPage from '@/pages/ResearchPage'
import PaperTradingPage from '@/pages/PaperTradingPage'

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<MainLayout />}>
          <Route path="/" element={<Navigate to="/markets" replace />} />
          <Route path="/markets" element={<MarketsPage />} />
          <Route path="/strategies" element={<StrategiesPage />} />
          <Route path="/analytics" element={<AnalyticsPage />} />
          <Route path="/settings" element={<SettingsPage />} />
          <Route path="/research" element={<ResearchPage />} />
          <Route path="/paper-trading" element={<PaperTradingPage />} />
        </Route>
      </Routes>
      <ChatInterface />
    </BrowserRouter>
  )
}
