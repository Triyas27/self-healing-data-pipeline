import { Route, Routes } from "react-router-dom";
import Nav from "./components/Nav";
import Dashboard from "./pages/Dashboard";
import Quarantine from "./pages/Quarantine";

function App() {
  return (
    <div className="app-shell">
      <Nav />
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/quarantine" element={<Quarantine />} />
      </Routes>
    </div>
  );
}

export default App;
