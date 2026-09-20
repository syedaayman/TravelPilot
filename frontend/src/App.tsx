import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import PlannerPage from './pages/PlannerPage';
import TripDashboardPage from './pages/TripDashboardPage';
import { ErrorBoundary } from './components/common/ErrorBoundary';

function App() {
  return (
    <BrowserRouter>
      <ErrorBoundary>
        <div className="min-h-screen bg-slate-50 text-slate-900 font-sans selection:bg-blue-600 selection:text-white">
          <header className="bg-white border-b border-slate-200 sticky top-0 z-40 shadow-sm">
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
              <a href="/" className="flex items-center gap-3 group">
                <div className="w-10 h-10 rounded-xl bg-blue-600 text-white flex items-center justify-center font-bold text-lg shadow-sm">
                  ✈️
                </div>
                <div>
                  <h1 className="text-lg font-black tracking-wider text-slate-900 flex items-center gap-1.5">
                    TRAVEL<span className="text-blue-600">PILOT</span>
                  </h1>
                  <p className="text-[10px] text-slate-500 font-mono tracking-widest uppercase">Intelligent Travel System</p>
                </div>
              </a>

              <div className="flex items-center gap-4 text-xs font-mono">
                <span className="hidden sm:flex items-center gap-1.5 px-3 py-1 rounded-full bg-blue-50 border border-blue-200 text-blue-700 font-semibold">
                  <span className="w-2 h-2 rounded-full bg-blue-600 animate-pulse"></span>
                  DETERMINISTIC ENGINE ACTIVE
                </span>
              </div>
            </div>
          </header>

          <main>
            <Routes>
              <Route path="/" element={<PlannerPage />} />
              <Route path="/trip/:tripId" element={<TripDashboardPage />} />
              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
          </main>
        </div>
      </ErrorBoundary>
    </BrowserRouter>
  );
}

export default App;
