import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
const apiProxy = process.env.THREATGRAPH_API_PROXY || "http://127.0.0.1:8000";
export default defineConfig({
  plugins: [react()],
  server: { port: 3000, proxy: { "/api": apiProxy } },
  preview: { port: 3000, proxy: { "/api": apiProxy } },
  build: {
    rollupOptions: {
      output: {
        manualChunks: {
          graph: ["cytoscape"],
          charts: ["recharts"],
          react: ["react", "react-dom", "react-router-dom"],
        },
      },
    },
  },
});
