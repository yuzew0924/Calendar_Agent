import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

export default defineConfig({
  plugins: [react()],
  envDir: "..",
  server: {
    host: "127.0.0.1",
    port: 5173
  },
  test: {
    environment: "jsdom",
    env: {
      VITE_API_BASE_URL: "http://localhost:8000"
    },
    setupFiles: "./src/test/setup.ts"
  }
});
