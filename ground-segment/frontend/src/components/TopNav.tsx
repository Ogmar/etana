import { NavLink } from "react-router-dom";

export function TopNav() {
  return (
    <div className="topnav">
      <div className="brand">ETANA<span>·</span>MISSION CONSOLE</div>
      <nav className="navlinks">
        <NavLink to="/" end className={({ isActive }) => (isActive ? "on" : "")}>
          DASHBOARD
        </NavLink>
        <NavLink to="/vehicle" className={({ isActive }) => (isActive ? "on" : "")}>
          VEHICLE
        </NavLink>
      </nav>
    </div>
  );
}
