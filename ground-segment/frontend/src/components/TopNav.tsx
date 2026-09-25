import { Link, NavLink } from "react-router-dom";

export function TopNav() {
  return (
    <div className="topnav">
      <Link to="/" className="brand">
        <span className="brand-main">ETANA</span>
        <span className="brand-sep">·</span>
        <span className="brand-sub">MISSION CONSOLE</span>
      </Link>
      <nav className="navlinks">
        <NavLink to="/" end className={({ isActive }) => (isActive ? "on" : "")}>
          HOME
        </NavLink>
        <NavLink to="/vehicle" className={({ isActive }) => (isActive ? "on" : "")}>
          VEHICLE
        </NavLink>
      </nav>
      <div className="sep" />
      <NavLink to="/dashboard" className={({ isActive }) => `dashboard-cta ${isActive ? "on" : ""}`}>
        Dashboard
      </NavLink>
    </div>
  );
}
