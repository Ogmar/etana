import { lazy, Suspense } from "react";
import { Route, Routes } from "react-router-dom";
import { TopNav } from "./components/TopNav";
import DashboardPage from "./pages/DashboardPage";

const VehiclePage = lazy(() => import("./pages/VehiclePage"));

export default function App() {
  return (
    <div className="app-shell">
      <TopNav />
      <div className="app-body">
        <Routes>
          <Route path="/" element={<DashboardPage />} />
          <Route
            path="/vehicle"
            element={(
              <Suspense fallback={<div className="empty">Loading…</div>}>
                <VehiclePage />
              </Suspense>
            )}
          />
        </Routes>
      </div>
    </div>
  );
}
