import { Link, NavLink } from "react-router-dom";

export function TopNav() {
  return (
    <div className="topnav">
      <Link to="/" className="brand">
        ETANA<span>·</span>MISSION CONSOLE
      </Link>
      <nav className="navlinks">
        <NavLink to="/" end className={({ isActive }) => (isActive ? "on" : "")}>
          HOME
        </NavLink>
        <NavLink to="/dashboard" className={({ isActive }) => (isActive ? "on" : "")}>
          DASHBOARD
        </NavLink>
        <NavLink to="/vehicle" className={({ isActive }) => (isActive ? "on" : "")}>
          VEHICLE
        </NavLink>
      </nav>
    </div>
  );
}
