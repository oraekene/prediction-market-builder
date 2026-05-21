export default function StatusBar() {
  return (
    <footer className="border-t border-gray-800 bg-gray-950 px-6 py-1.5">
      <div className="flex items-center justify-between text-xs text-gray-500">
        <span>Polymarket: Live | Kalshi: Live | Drift: Live</span>
        <span>Last updated: {new Date().toLocaleTimeString()}</span>
      </div>
    </footer>
  )
}
