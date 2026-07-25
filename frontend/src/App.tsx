import { lazy, Suspense } from "react";
import { Route, Routes, useLocation } from "react-router-dom";
import ErrorBoundary from "./components/ErrorBoundary";
import Nav from "./components/Nav";

const Dashboard = lazy(() => import("./pages/Dashboard"));
const Quarantine = lazy(() => import("./pages/Quarantine"));
const RunDetail = lazy(() => import("./pages/RunDetail"));

function App() {
  const location = useLocation();
  return (
    <div className="app-shell">
      <Nav />
      {/* Keyed by path so navigating away from a crashed page mounts a fresh
          boundary instead of staying stuck in its errored state. */}
      <ErrorBoundary key={location.pathname}>
        <Suspense fallback={<div className="empty-state">Loading...</div>}>
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/quarantine" element={<Quarantine />} />
            <Route path="/runs/:id" element={<RunDetail />} />
          </Routes>
        </Suspense>
      </ErrorBoundary>
    </div>
  );
}

export default App;
