// frontend/web/vite.config.js
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig(({ command, mode }) => ({
  plugins: [react()],
  server: {
    port: 5173,
    host: true, // allow LAN access if you run with --host
    strictPort: true,
    cors: false, // we use proxy instead of CORS during dev
    watch: { usePolling: false },
    proxy: {
      // REST → FastAPI
      "^/v1($|/)": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
        secure: false,
        ws: false,
      },
      // Health/meta
      "^/health($|/)": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
        secure: false,
      },
      // WebSocket endpoints
      "^/ws($|/)": {
        target: "ws://127.0.0.1:8000",
        changeOrigin: true,
        ws: true,
        secure: false,
      },
    },
  },
  preview: {
    port: 5173,
    strictPort: true,
  },
}));
