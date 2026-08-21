import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    // Proxy API calls to the Django server during development, so the frontend
    // can call /api/... without cross-origin issues.
    proxy: {
      "/api": "http://localhost:8000",
    },
  },
});
