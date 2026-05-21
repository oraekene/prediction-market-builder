import { Outlet } from 'react-router-dom'
import Header from './Header'
import Sidebar from './Sidebar'
import StatusBar from './StatusBar'

export default function MainLayout() {
  return (
    <div className="flex h-screen flex-col bg-gray-900 text-gray-100">
      <Header />
      <div className="flex flex-1 overflow-hidden">
        <Sidebar />
        <main className="flex-1 overflow-auto p-6">
          <Outlet />
        </main>
      </div>
      <StatusBar />
    </div>
  )
}
