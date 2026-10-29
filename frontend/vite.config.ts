import preact from "@preact/preset-vite";
import { defineConfig } from "vite";

const BACKEND = "http://127.0.0.1:8000";

export default defineConfig({
  plugins: [preact()],
  server: {
    host: "127.0.0.1",
    port: 5173,
    proxy: {
      "/api": { target: BACKEND, changeOrigin: true, ws: true },
      "/icons": { target: BACKEND, changeOrigin: true },
      "/wallpaper": { target: BACKEND, changeOrigin: true },
      "/type": { target: BACKEND, changeOrigin: true },
    },
  },
});
