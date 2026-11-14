/// <reference types="vitest/config" />
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// The FastAPI service from `uvicorn app.main:app --reload` in backend/.
const BACKEND_URL = "http://localhost:8000";

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      "/api": BACKEND_URL,
      "/mcp": BACKEND_URL,
      "/healthz": BACKEND_URL,
    },
  },
  test: {
    environment: "node",
  },
});
