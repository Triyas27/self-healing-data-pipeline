import { NavLink } from "react-router-dom";

export default function Nav() {
  return (
    <nav className="nav">
      <h1>Self-Healing Pipeline</h1>
      <NavLink to="/" end className={({ isActive }) => (isActive ? "active" : "")}>
        Dashboard
      </NavLink>
      <NavLink to="/quarantine" className={({ isActive }) => (isActive ? "active" : "")}>
        Quarantine
      </NavLink>
    </nav>
  );
}
