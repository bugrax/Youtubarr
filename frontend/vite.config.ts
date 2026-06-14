import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Build into the FastAPI static dir; served at "/".
export default defineConfig({
  plugins: [react()],
  build: { outDir: "dist", emptyOutDir: true },
  server: { proxy: { "/api": "http://127.0.0.1:8585" } },
});
