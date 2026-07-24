import { Route, Routes, useLocation } from "react-router-dom";
import ErrorBoundary from "./components/ErrorBoundary";
import Nav from "./components/Nav";
import Dashboard from "./pages/Dashboard";
import Quarantine from "./pages/Quarantine";
import RunDetail from "./pages/RunDetail";

function App() {
  const location = useLocation();
  return (
    <div className="app-shell">
      <Nav />
      {/* Keyed by path so navigating away from a crashed page mounts a fresh
          boundary instead of staying stuck in its errored state. */}
      <ErrorBoundary key={location.pathname}>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/quarantine" element={<Quarantine />} />
          <Route path="/runs/:id" element={<RunDetail />} />
        </Routes>
      </ErrorBoundary>
    </div>
  );
}

export default App;
