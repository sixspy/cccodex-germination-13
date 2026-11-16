import { defineConfig } from "vite";
import { svelte } from "@sveltejs/vite-plugin-svelte";

export default defineConfig({
  plugins: [svelte()],
  server: {
    port: 3213,
    strictPort: true,
    proxy: { "/api": "http://127.0.0.1:8213" },
  },
});
