import path from "node:path";

import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// Browser code fetches `/api/...`; the dev server proxies those to the FastAPI
// backend so we never have to worry about CORS. In docker-compose the backend
// is reachable as `http://backend:8000`; outside the compose network override
// via the `VITE_BACKEND_URL` environment variable.
const backendUrl = process.env.VITE_BACKEND_URL ?? "http://backend:8000";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  server: {
    host: "0.0.0.0",
    port: 5173,
    proxy: {
      "/api": {
        target: backendUrl,
        changeOrigin: true,
        rewrite: (p) => p.replace(/^\/api/, ""),
      },
    },
  },
});
