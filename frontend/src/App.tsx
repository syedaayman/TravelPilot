import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import PlannerPage from './pages/PlannerPage';
import TripDashboardPage from './pages/TripDashboardPage';
import { ErrorBoundary } from './components/common/ErrorBoundary';

function App() {
  return (
    <BrowserRouter>
      <ErrorBoundary>
        <div className="min-h-screen bg-gray-50 text-gray-900 font-sans">
          <header className="bg-white border-b border-gray-200 sticky top-0 z-30">
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="text-2xl">✈️</span>
                <h1 className="text-xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-blue-600 to-indigo-600">TravelPilot</h1>
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
